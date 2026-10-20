#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Spark 演示仓库：复用 sqlite 数据，写成 parquet，__dq_rid__ 对齐 ground truth。

用法：
    python scripts/make_demo_spark.py
    python scripts/dq.py check --db spark
"""
import glob
import os
import shutil
import sqlite3
import sys

import make_demo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
WAREHOUSE = os.path.join(DATA, "spark_warehouse")

TYPE_MAP = {"INTEGER": "long", "REAL": "double", "TEXT": "string"}


def find_java_home():
    if os.environ.get("JAVA_HOME"):
        return os.environ["JAVA_HOME"]
    base = os.path.expanduser("~/.dsh/java")
    if os.path.isdir(base):
        for name in sorted(os.listdir(base), reverse=True):
            p = os.path.join(base, name)
            if os.path.isdir(p) and os.path.exists(os.path.join(p, "bin", "java.exe")):
                return p
    return None


def _spark():
    from pyspark.sql import SparkSession

    java_home = find_java_home()
    if java_home:
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = os.path.join(java_home, "bin") + os.pathsep + os.environ.get("PATH", "")
    hadoop_home = os.path.expanduser("~/.dsh/hadoop")
    if os.path.isdir(hadoop_home):
        os.environ["HADOOP_HOME"] = hadoop_home
        os.environ["PATH"] = os.path.join(hadoop_home, "bin") + os.pathsep + os.environ.get("PATH", "")
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
    return (SparkSession.builder
            .master("local[2]")
            .appName("dq-sentinel-demo")
            .config("spark.ui.enabled", "false")
            .config("spark.sql.shuffle.partitions", "2")
            .config("spark.sql.warehouse.dir", os.path.join(DATA, "spark-warehouse"))
            .config("spark.hadoop.hadoop.home.dir", hadoop_home if os.path.isdir(hadoop_home) else "")
            .getOrCreate())


def build_spark(dirty=True, warehouse=WAREHOUSE):
    from pyspark.sql.types import StructField, StructType, LongType, DoubleType, StringType

    type_map = {"INTEGER": LongType(), "REAL": DoubleType(), "TEXT": StringType()}

    sqlite_db, gt, manifest = make_demo.build(dirty=dirty)
    if os.path.isdir(warehouse):
        shutil.rmtree(warehouse)
    os.makedirs(warehouse, exist_ok=True)

    spark = _spark()
    src = sqlite3.connect(sqlite_db)
    src.row_factory = sqlite3.Row
    try:
        for table in ("users", "products", "orders"):
            cols = [dict(r) for r in src.execute(f"PRAGMA table_info({table})")]
            rows = [tuple(r) for r in src.execute(f"SELECT rowid AS rid, * FROM {table}")]
            fields = [StructField("__dq_rid__", LongType())] + [
                StructField(c["name"], type_map.get((c["type"] or "TEXT").upper(), StringType()))
                for c in cols
            ]
            ctx = spark.createDataFrame(rows, schema=StructType(fields))
            ctx.write.mode("overwrite").parquet(os.path.join(warehouse, table))
    finally:
        src.close()
        spark.stop()
    return warehouse


def register_views(spark, warehouse=WAREHOUSE):
    for path in sorted(glob.glob(os.path.join(warehouse, "*"))):
        if os.path.isdir(path):
            spark.read.parquet(path).createOrReplaceTempView(os.path.basename(path))


if __name__ == "__main__":
    path = build_spark()
    print("spark warehouse:", path)
