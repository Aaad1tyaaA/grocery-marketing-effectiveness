"""Create a self-contained database; no dependence on DBeaver's working directory."""
from pathlib import Path
import json
import os

import duckdb
from get_data import EXPECTED, ROOT


def literal(path):
    return "'" + path.as_posix().replace("'", "''") + "'"


def main():
    target = ROOT / "grocery.duckdb"
    if target.exists():
        raise FileExistsError(f"Preserving existing database: {target}. Rename it before rebuilding.")
    staging = ROOT / "grocery.building.duckdb"
    if staging.exists():
        raise FileExistsError(f"Inspect the previous incomplete build first: {staging}")
    report = {"duckdb_version": duckdb.__version__, "tables": {}, "checks": {}}
    with duckdb.connect(str(staging)) as con:
        con.execute("SET memory_limit = '512MB'")
        con.execute("SET threads = 1")
        con.execute("SET TimeZone = 'UTC'")
        for name, expected in EXPECTED.items():
            source = ROOT / "data/parquet" / (name + ".parquet")
            con.execute(f'CREATE TABLE "{name}" AS SELECT * FROM read_parquet({literal(source)})')
            count, fingerprint = con.execute(f'SELECT count(*), bit_xor(hash(t))::VARCHAR FROM "{name}" t').fetchone()
            source_count, source_hash = con.execute(f'SELECT count(*), bit_xor(hash(t))::VARCHAR FROM read_parquet({literal(source)}) t').fetchone()
            assert count == source_count == expected, f"Row count failed: {name}"
            assert fingerprint == source_hash, f"Content fingerprint failed: {name}"
            report["tables"][name] = {"rows": count, "content_fingerprint": fingerprint,
                "schema": con.execute(f'DESCRIBE "{name}"').fetchall()}
            print(f"Verified {name}: {count:,}", flush=True)
        household_count = con.execute("SELECT count(DISTINCT household_id) FROM transactions").fetchone()[0]
        assert household_count == 2469
        for name, key in [("products", "product_id"), ("demographics", "household_id"), ("campaign_descriptions", "campaign_id")]:
            duplicates, missing = con.execute(f'SELECT count(*) - count(DISTINCT {key}), count(*) FILTER (WHERE {key} IS NULL) FROM {name}').fetchone()
            assert duplicates == missing == 0, f"Dimension key failed: {name}"
        profile = con.execute("""SELECT min(transaction_timestamp), max(transaction_timestamp),
            min(week), max(week), count(DISTINCT basket_id), round(sum(sales_value), 2),
            count(*) FILTER (WHERE quantity=0 AND sales_value=0) FROM transactions""").fetchone()
        assert profile[-1] == 8820
        report["checks"] = {"households": household_count, "transaction_profile": profile,
            "source_parquet_fingerprints_match": True, "dimension_keys_unique_and_not_null": True}
        con.execute("CHECKPOINT")
    # Reopen in a separate connection after all writes have closed.
    with duckdb.connect(str(staging), read_only=True) as con:
        assert len(con.execute("SHOW TABLES").fetchall()) == 8
        assert con.execute("SELECT count(*) FROM transactions").fetchone()[0] == EXPECTED["transactions"]
    os.rename(staging, target)
    report["database"] = target.name
    (ROOT / "docs/verification.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Ready: {target}", flush=True)


if __name__ == "__main__":
    main()
