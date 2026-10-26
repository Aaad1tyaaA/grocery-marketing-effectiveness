"""Build a separately named, verified phase-1 database without touching the open original."""
from pathlib import Path
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import duckdb
from provenance import build_inputs

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ["transactions", "promotions", "campaigns", "campaign_descriptions", "coupons",
           "coupon_redemptions", "demographics", "products"]


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def identifier(value):
    return '"' + value.replace('"', '""') + '"'


def export(con, query, path):
    cursor = con.execute(query)
    with path.open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.writer(output)
        writer.writerow([c[0] for c in cursor.description])
        while rows := cursor.fetchmany(1000):
            writer.writerows(rows)


def main():
    target = ROOT / "grocery_phase1.duckdb"
    staging = ROOT / "grocery_phase1.building.duckdb"
    if target.exists() or staging.exists():
        raise FileExistsError("Preserving existing phase-1 files. Rename the previous database before rebuilding.")
    output = ROOT / "exports/phase1"
    output.mkdir(parents=True, exist_ok=True)
    baseline = json.loads((ROOT / "docs/verification.json").read_text(encoding="utf-8"))["tables"]
    report = {"built_at_utc": datetime.now(timezone.utc).isoformat(), "duckdb_version": duckdb.__version__,
              "database": target.name, "raw_integrity": {}, "model_counts": {}, "checks": []}
    with duckdb.connect(str(staging)) as con:
        con.execute("SET memory_limit='512MB'")
        con.execute("SET threads=1")
        con.execute("SET TimeZone='UTC'")
        for name in SOURCES:
            path = (ROOT / "data/parquet" / f"{name}.parquet").as_posix()
            con.execute(f"CREATE TABLE {identifier(name)} AS SELECT * FROM read_parquet({quote(path)})")
            actual = con.execute(f"SELECT count(*),bit_xor(hash(t))::VARCHAR FROM {identifier(name)} t").fetchone()
            assert actual == (baseline[name]["rows"], baseline[name]["content_fingerprint"]), f"Parquet differs from verified source: {name}"
            report["raw_integrity"][name] = {"rows": actual[0], "fingerprint": actual[1]}
            print(f"Source verified: {name} ({actual[0]:,})", flush=True)

        # Save every column's missingness, cardinality, and schema as runnable SQL.
        columns = []
        for name in SOURCES:
            for column, dtype, *_ in con.execute(f"DESCRIBE {identifier(name)}").fetchall():
                columns.append(f"SELECT {quote(name)} AS table_name,{quote(column)} AS column_name,{quote(dtype)} AS data_type,"
                    f"count(*) AS total_rows,count(*) FILTER(WHERE {identifier(column)} IS NULL) AS null_rows,"
                    f"count(DISTINCT {identifier(column)}) AS distinct_non_null FROM {identifier(name)}")
        column_sql = "CREATE OR REPLACE TABLE profile_columns AS\n" + "\nUNION ALL\n".join(columns) + ";\n"
        (ROOT / "sql/00a_profile_columns.sql").write_text(column_sql, encoding="utf-8")
        con.execute("BEGIN")
        try:
            for file in ["00_profile.sql", "00a_profile_columns.sql", "01_model.sql", "01b_anomalies.sql", "01c_verify.sql"]:
                print(f"Running {file} ...", flush=True)
                con.execute((ROOT / "sql" / file).read_text(encoding="utf-8"))
            critical_nulls = con.execute("""SELECT sum(null_rows) FROM profile_columns
                WHERE (table_name='transactions' AND column_name IN
                    ('household_id','store_id','basket_id','product_id','quantity','sales_value','retail_disc','coupon_disc','coupon_match_disc','week','transaction_timestamp'))
                   OR (table_name='promotions')
                   OR (table_name='products' AND column_name='product_id')
                   OR (table_name='demographics' AND column_name='household_id')
                   OR (table_name='campaign_descriptions')""").fetchone()[0]
            con.execute("INSERT INTO phase1_checks VALUES ('required_source_fields_not_null',?)", [critical_nulls == 0])
            for name in SOURCES:
                actual = con.execute(f"SELECT count(*),bit_xor(hash(t))::VARCHAR FROM {identifier(name)} t").fetchone()
                saved = report["raw_integrity"][name]
                assert actual == (saved["rows"], saved["fingerprint"]), f"Raw table changed: {name}"
            con.execute("INSERT INTO phase1_checks VALUES ('eight_raw_tables_unchanged',true)")
            report["checks"] = [{"name": n, "passed": bool(p)} for n,p in con.execute("SELECT * FROM phase1_checks ORDER BY check_name").fetchall()]
            failed = [x["name"] for x in report["checks"] if not x["passed"]]
            assert not failed, f"Model validation failed: {failed}"
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

        tables = [x[0] for x in con.execute("SHOW TABLES").fetchall()]
        for name in tables:
            if name not in SOURCES:
                report["model_counts"][name] = con.execute(f"SELECT count(*) FROM {identifier(name)}").fetchone()[0]
            if name.startswith("profile_") or name in ("daily_anomalies", "basket_anomalies", "phase1_checks"):
                export(con, f"SELECT * FROM {identifier(name)}", output / f"{name}.csv")
        export(con,"SELECT * FROM fact_sales ORDER BY basket_id,product_id LIMIT 100", output / "fact_sales_sample.csv")
        export(con,"SELECT * FROM daily_sales ORDER BY day",output / "daily_sales.csv")
        top_baskets = """SELECT * FROM fact_sales WHERE basket_id IN
            (SELECT basket_id FROM basket_anomalies ORDER BY basket_value DESC LIMIT 5)
            ORDER BY basket_id,sales_value DESC"""
        export(con,top_baskets,output / "top_five_basket_lines.csv")
        report["transaction_summary"] = dict(zip([d[0] for d in con.execute("SELECT * FROM profile_transaction_summary").description],con.fetchone()))
        report["promotion_quality"] = dict(zip([d[0] for d in con.execute("SELECT * FROM profile_promotion_quality").description],con.fetchone()))
        report["non_grocery"] = con.execute("SELECT is_non_grocery,count(*),round(sum(sales_value),2) FROM fact_sales GROUP BY 1 ORDER BY 1").fetchall()
        report["unknown_products"] = con.execute("SELECT count(*),sum(line_items),round(sum(sales_usd),2) FROM profile_missing_products").fetchone()
        report["partially_observed_campaigns"] = con.execute("SELECT campaign_id FROM dim_campaign WHERE partially_observed ORDER BY campaign_id::INTEGER").fetchall()
        report["missing_days"] = con.execute("SELECT day FROM profile_missing_days ORDER BY day").fetchall()
        report["relationships"] = con.execute("SELECT * FROM profile_relationships ORDER BY check_name").fetchall()
        report["anomalous_dates"] = con.execute("SELECT day,round(robust_z,2) FROM daily_anomalies ORDER BY robust_z DESC").fetchall()
        report["schema"] = {name:con.execute(f"DESCRIBE {identifier(name)}").fetchall() for name in tables}
        report['build_inputs_sha256']=build_inputs(ROOT,['scripts/build_phase1.py','scripts/write_phase1_docs.py']+
            ['sql/'+name for name in ['00_profile.sql','00a_profile_columns.sql','01_model.sql','01b_anomalies.sql','01c_verify.sql']])
        con.execute("CHECKPOINT")
    with duckdb.connect(str(staging), read_only=True) as con:
        assert con.execute("SELECT bool_and(passed) FROM phase1_checks").fetchone()[0]
    os.rename(staging,target)
    (ROOT / "docs/phase1_verification.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    subprocess.run([sys.executable,str(ROOT / "scripts/write_phase1_docs.py")],check=True)
    print(f"PASS: {len(report['checks'])} checks; ready: {target}",flush=True)


if __name__ == "__main__":
    main()
