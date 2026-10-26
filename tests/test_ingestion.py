"""Regression check for the compact reader, including R nulls and categorical dates."""
from pathlib import Path
import sys

import pandas as pd
import pyreadr
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from get_data import read_compact


@pytest.mark.parametrize("name", [
    "campaigns", "campaign_descriptions", "coupons", "coupon_redemptions", "demographics", "products",
])
def test_compact_reader_matches_standard(name):
    path = ROOT / "data/raw" / (name + ".rda")
    if not path.exists():
        pytest.skip("Download source data first")
    standard = next(iter(pyreadr.read_r(path).values()))
    pd.testing.assert_frame_equal(read_compact(path), standard)
