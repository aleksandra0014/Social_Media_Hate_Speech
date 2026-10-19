"""Paths, CSV I/O and params shared by the preprocessing entry points."""
import json
from pathlib import Path

import pandas as pd
import yaml

PARAMS_FILE = Path('params.yaml')
RAW_ROOT = Path('data/raw')
INTERIM_ROOT = Path('data/interim')
SOURCES = ('posts', 'comments')


def load_params(section):
    params = yaml.safe_load(PARAMS_FILE.read_text(encoding='utf-8')) or {}
    return params.get(section, {})


def read_csv(path):
    # Ids stay strings; collectors write UTF-8 with BOM.
    return pd.read_csv(path, encoding='utf-8-sig', dtype=str, keep_default_na=False)


def write_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding='utf-8-sig')


def write_json(data, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
