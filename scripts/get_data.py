"""Download the full, commit-pinned Complete Journey sources and convert to Parquet."""
from pathlib import Path
import hashlib
import json
import time
import sys
from urllib.request import Request, urlopen

import pyreadr
from pyreadr._pyreadr_parser import PyreadrParser
from pyreadr.pyreadr import _parse

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "transactions": 1_469_307, "promotions": 20_940_529,
    "campaigns": 6_589, "campaign_descriptions": 27,
    "coupons": 116_204, "coupon_redemptions": 2_102,
    "demographics": 801, "products": 92_331,
}


class CompactParser(PyreadrParser):
    # pyreadr 0.5.8 creates a new Python string for every repeated label.
    # Interning keeps one copy of each product/store label for this large RDS.
    def handle_text_value(self, name, index):
        if self.parse_current_table:
            self.current_table.columns[self.column_index].append(sys.intern(name) if isinstance(name, str) else name)


def read_compact(path):
    parser = CompactParser()
    _parse(parser, path)
    parser.finish_text_column()
    assert len(parser.table_data) == 1
    return parser.table_data[0].convert_to_dataframe()


def fetch(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": "GroceryProjectSetup"}), timeout=120) as response:
                return response.read()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)


def main():
    raw, parquet = ROOT / "data/raw", ROOT / "data/parquet"
    raw.mkdir(parents=True, exist_ok=True)
    parquet.mkdir(parents=True, exist_ok=True)
    manifest_path = ROOT / "docs/source_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        api = "https://api.github.com/repos/bradleyboehmke/completejourney"
        commit = json.loads(fetch(api + "/commits/master"))["sha"]
        files = json.loads(fetch(api + "/contents/data?ref=" + commit))
        manifest = {"repository": "https://github.com/bradleyboehmke/completejourney", "commit": commit,
                    "files": [f for f in files if Path(f["name"]).stem in EXPECTED]}
        assert len(manifest["files"]) == 8, "Expected eight full source files"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for info in manifest["files"]:
        path = raw / info["name"]
        name = path.stem
        if not path.exists():
            part = path.with_suffix(path.suffix + ".part")
            part.write_bytes(fetch(info["download_url"]))
            part.replace(path)
        payload = path.read_bytes()
        assert len(payload) == info["size"], f"Wrong source size: {name}"
        git_sha = hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
        assert git_sha == info["sha"], f"Source integrity failed: {name}"
        info["sha256"] = hashlib.sha256(payload).hexdigest()
        del payload
        print(f"Converting {name} ...", flush=True)
        frame = read_compact(path)
        assert len(frame) == EXPECTED[name], f"Unexpected row count: {name}: {len(frame)}"
        # Identifiers and placement codes are labels, including numeric-looking codes.
        for column in frame.columns:
            if column.endswith("_id") or column in ("display_location", "mailer_location", "coupon_upc"):
                if frame[column].dtype.kind not in ("O", "U", "S") and str(frame[column].dtype) != "category":
                    frame[column] = frame[column].astype("string")
        target = parquet / (name + ".parquet")
        temporary = target.with_suffix(".parquet.part")
        frame.to_parquet(temporary, index=False, compression="zstd")
        temporary.replace(target)
        info['parquet_sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
        info["rows"] = len(frame)
        info["columns"] = list(frame.columns)
        print(f"  {name}: {len(frame):,} rows", flush=True)
        del frame
    manifest["pyreadr_version"] = pyreadr.__version__
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
