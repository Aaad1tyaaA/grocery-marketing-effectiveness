"""Fetch the checksum-pinned scientific mirror and preserve the original experiment rows."""
from pathlib import Path
from urllib.request import Request,urlopen
import gzip
import hashlib
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
URL='https://hillstorm1.s3.us-east-2.amazonaws.com/hillstorm_no_indices.csv.gz'
MIRROR_MD5='a68a81291f53a14f4e29002629803ba3'
CSV_SHA256='00a6a868e05a9ffe7382da51629f6d6dce88c5acfc945e79d314ebc78fd3a2c0'
ORIGINAL='http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv'


def main():
    raw=ROOT/'data/raw/hillstrom.csv'
    compressed=ROOT/'data/raw/hillstrom.csv.gz'
    metadata=ROOT/'docs/hillstrom_source.json'
    if metadata.exists():
        saved=json.loads(metadata.read_text(encoding='utf-8'))
        for path,key in [(raw,'csv_sha256'),(ROOT/'data/parquet/hillstrom.parquet','parquet_sha256')]:
            if path.exists():
                assert hashlib.sha256(path.read_bytes()).hexdigest()==saved[key],f'Changed Hillstrom input: {path.name}'
    if not raw.exists():
        if not compressed.exists():
            with urlopen(Request(URL,headers={'User-Agent':'GroceryMarketingProject/1.0'}),timeout=60) as response:
                payload=response.read()
            assert hashlib.md5(payload).hexdigest()==MIRROR_MD5,'Mirror checksum mismatch'
            compressed.write_bytes(payload)
        payload=compressed.read_bytes()
        assert hashlib.md5(payload).hexdigest()==MIRROR_MD5,'Mirror checksum mismatch'
        raw.write_bytes(gzip.decompress(payload))
    assert hashlib.sha256(raw.read_bytes()).hexdigest()==CSV_SHA256,'CSV differs from the pinned mirror copy'
    frame=pd.read_csv(raw)
    assert len(frame)==64000 and len(frame.columns)==12
    target=ROOT/'data/parquet/hillstrom.parquet'
    temporary=target.with_suffix('.parquet.part')
    frame.to_parquet(temporary,index=False,compression='zstd')
    temporary.replace(target)
    info={'original_url':ORIGINAL,'download_url':URL,'mirror_md5':MIRROR_MD5,
          'mirror_documentation':'https://github.com/maks-sh/scikit-uplift/blob/master/sklift/datasets/datasets.py',
          'experiment_description':'https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html',
          'csv_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),
          'parquet_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
          'rows':len(frame),'columns':list(frame.columns),'row_order':'preserved; source_row assigned as one-based CSV position',
          'download_note':'Original HTTPS endpoint failed certificate validation; used scientific package mirror with published MD5.'}
    metadata.write_text(json.dumps(info,indent=2),encoding='utf-8')
    print('Hillstrom source verified:',len(frame),'rows',info['csv_sha256'])


if __name__=='__main__':
    main()
