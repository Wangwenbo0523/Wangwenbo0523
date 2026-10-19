#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成演示数据：3 张业务表（用户/商品/订单），注入 20 类脏数据并记录 ground truth。

用法：
    python scripts/make_demo.py            # 生成 data/demo.db + data/ground_truth.json
"""
import json
import os
import random
import sqlite3
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DB = os.path.join(DATA, "demo.db")
GT = os.path.join(DATA, "ground_truth.json")
MANIFEST = os.path.join(DATA, "manifest.json")

CITIES = ["北京", "上海", "广州", "深圳", "杭州"]
CATEGORIES = ["数码", "家电", "服饰", "食品"]
STATUSES = ["待支付", "已支付", "已发货", "已完成"]

random.seed(42)


def _now():
    return datetime.now()


def _fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def create_schema(c):
    c.executescript(
        """
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS orders;

        CREATE TABLE users (
            id INTEGER,
            name TEXT,
            phone TEXT,
            email TEXT,
            signup_date TEXT,
            city TEXT
        );
        CREATE TABLE products (
            id INTEGER,
            name TEXT,
            category TEXT,
            price REAL,
            stock INTEGER
        );
        CREATE TABLE orders (
            id INTEGER,
            user_id INTEGER,
            product_id INTEGER,
            qty INTEGER,
            unit_price REAL,
            amount REAL,
            status TEXT,
            created_at TEXT
        );
        """
    )


def seed_clean(c):
    users, products, orders = [], [], []
    for i in range(1, 201):
        d = (_now() - timedelta(days=random.randint(0, 300))).strftime("%Y-%m-%d")
        users.append((i, f"用户{i:03d}", f"138{random.randint(10000000, 99999999)}",
                      f"user{i:03d}@example.com", d, random.choice(CITIES)))
    for i in range(50):
        pid = 100 + i
        price = round(random.uniform(10, 2000), 2)
        products.append((pid, f"商品{i:02d}", random.choice(CATEGORIES), price,
                         random.randint(0, 500)))
    price_by_pid = {p[0]: p[3] for p in products}
    for i in range(800):
        pid = random.choice(list(price_by_pid))
        qty = random.randint(1, 5)
        amount = round(qty * price_by_pid[pid], 2)
        created = _now() - timedelta(days=random.randint(0, 5),
                                     hours=random.randint(0, 23))
        orders.append((10000 + i, random.randint(1, 200), pid, qty,
                       price_by_pid[pid], amount,
                       random.choice(STATUSES), _fmt(created)))
    c.executemany("INSERT INTO users VALUES (?,?,?,?,?,?)", users)
    c.executemany("INSERT INTO products VALUES (?,?,?,?,?)", products)
    c.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?)", orders)


def inject(c, gt):
    """注入 20 类脏数据，返回注入清单。"""
    manifest = []

    def add(table, rowid, issue):
        gt.append({"table": table, "rowid": rowid, "issue": issue})
        manifest.append({"table": table, "rowid": rowid, "issue": issue})

    # ---------- users ----------
    cur = c.execute("INSERT INTO users VALUES (NULL,'用户NULL','13800000000','null@example.com',?, '北京')",
                    ((_now() - timedelta(days=30)).strftime("%Y-%m-%d"),))
    add("users", cur.lastrowid, "id 为空")

    cur = c.execute("INSERT INTO users SELECT id,name,phone,email,signup_date,city FROM users WHERE rowid=5")
    add("users", 5, "id 重复（原行）")
    add("users", cur.lastrowid, "id 重复（副本）")

    c.execute("UPDATE users SET phone='12345' WHERE rowid=7")
    add("users", 7, "手机号格式错误")

    c.execute("UPDATE users SET email='not-an-email' WHERE rowid=9")
    add("users", 9, "邮箱格式错误")

    c.execute("UPDATE users SET signup_date=? WHERE rowid=11",
              ((_now() + timedelta(days=30)).strftime("%Y-%m-%d"),))
    add("users", 11, "注册日期在未来")

    c.execute("UPDATE users SET city='火星' WHERE rowid=13")
    add("users", 13, "城市不在枚举内")

    c.execute("UPDATE users SET name='   ' WHERE rowid=15")
    add("users", 15, "姓名为空")

    # ---------- products ----------
    c.execute("UPDATE products SET price=-10 WHERE rowid=2")
    add("products", 2, "价格为负")

    c.execute("UPDATE products SET price=NULL WHERE rowid=4")
    add("products", 4, "价格为空")

    c.execute("UPDATE products SET stock=-5 WHERE rowid=6")
    add("products", 6, "库存为负")

    c.execute("UPDATE products SET category='未知' WHERE rowid=8")
    add("products", 8, "类目不在枚举内")

    cur = c.execute("INSERT INTO products SELECT id,name,category,price,stock FROM products WHERE rowid=10")
    add("products", 10, "id 重复（原行）")
    add("products", cur.lastrowid, "id 重复（副本）")

    # ---------- orders ----------
    c.execute("UPDATE orders SET user_id=99999 WHERE rowid=5")
    add("orders", 5, "user_id 孤儿外键")

    c.execute("UPDATE orders SET product_id=88888 WHERE rowid=8")
    add("orders", 8, "product_id 孤儿外键")

    c.execute("UPDATE orders SET qty=0 WHERE rowid=11")
    add("orders", 11, "数量为 0")

    c.execute("UPDATE orders SET amount=amount+5 WHERE rowid=14")
    add("orders", 14, "金额与数量×单价不一致")

    c.execute("UPDATE orders SET status='未知状态' WHERE rowid=17")
    add("orders", 17, "状态不在枚举内")

    c.execute("UPDATE orders SET created_at=NULL WHERE rowid=20")
    add("orders", 20, "创建时间为空")

    c.execute("UPDATE orders SET created_at=? WHERE rowid=23",
              (_fmt(_now() - timedelta(days=10)),))
    add("orders", 23, "分区数据延迟（>7 天）")

    cur = c.execute("INSERT INTO orders SELECT id,user_id,product_id,qty,unit_price,amount,status,created_at FROM orders WHERE rowid=26")
    add("orders", 26, "id 重复（原行）")
    add("orders", cur.lastrowid, "id 重复（副本）")

    return manifest


def build(db=DB, gt_path=GT, manifest_path=MANIFEST):
    os.makedirs(os.path.dirname(db), exist_ok=True)
    if os.path.exists(db):
        os.remove(db)
    conn = sqlite3.connect(db)
    try:
        create_schema(conn)
        seed_clean(conn)
        gt, manifest = [], []
        # 注入器需要同时写 gt，这里用闭包包装
        manifest = inject(conn, gt)
        conn.commit()
    finally:
        conn.close()

    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump({"rows": gt}, f, ensure_ascii=False, indent=2)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"issues": manifest}, f, ensure_ascii=False, indent=2)
    return db, gt, manifest


if __name__ == "__main__":
    build()
    print("demo db:", DB)
    print("ground truth:", GT)
