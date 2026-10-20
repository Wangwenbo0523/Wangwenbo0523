#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 DuckDB 演示库：复用 sqlite 演示数据，附带 __dq_rid__ 以对齐 ground truth。

用法：
    python scripts/make_demo_duck.py            # data/demo.duckdb（含 20 类脏数据）
    python scripts/dq.py check --db data/demo.duckdb
"""
import os
import sqlite3

import duckdb

import make_demo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DUCK_DB = os.path.join(DATA, "demo.duckdb")

TYPE_MAP = {"INTEGER": "BIGINT", "REAL": "DOUBLE", "TEXT": "VARCHAR"}


def build(dirty=True, duck_db=DUCK_DB):
    sqlite_db, gt, manifest = make_demo.build(dirty=dirty)
    if os.path.exists(duck_db):
        os.remove(duck_db)
    dst = duckdb.connect(duck_db)
    src = sqlite3.connect(sqlite_db)
    src.row_factory = sqlite3.Row
    try:
        for table in ("users", "products", "orders"):
            cols = [dict(r) for r in src.execute(f"PRAGMA table_info({table})")]
            defs = ", ".join(
                f'"{c["name"]}" {TYPE_MAP.get((c["type"] or "TEXT").upper(), "VARCHAR")}'
                for c in cols
            )
            dst.execute(f'CREATE TABLE "{table}" (__dq_rid__ BIGINT, {defs})')
            rows = [tuple(r) for r in src.execute(f"SELECT rowid AS rid, * FROM {table}")]
            marks = ", ".join(["?"] * (len(cols) + 1))
            dst.executemany(f'INSERT INTO "{table}" VALUES ({marks})', rows)
    finally:
        src.close()
        dst.close()
    return duck_db


if __name__ == "__main__":
    path = build()
    print("duckdb demo:", path)
