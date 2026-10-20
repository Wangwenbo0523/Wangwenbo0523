#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dq-sentinel：数据质量巡检 Agent Skill 的命令行实现。

用法：
    python scripts/dq.py demo                 # 生成演示库 + 巡检 + 评测 + 报告
    python scripts/dq.py init                 # 只生成演示库（含 20 类脏数据）
    python scripts/dq.py check --fail-on P0   # 巡检；P0 违规时退出码 1（CI 门禁）
    python scripts/dq.py mark --table users --rowid 7 --rule "users.phone 手机号格式" --reason "测试账号"
    python scripts/dq.py suggest              # 从画像生成候选规则
    python scripts/dq.py suggest --llm        # 尝试调用 LLM 润色（需 DQ_LLM_BASE 等环境变量）
    python scripts/dq.py profile              # 输出表结构画像
    python scripts/dq.py evaluate             # 与 ground truth 对比
"""
import argparse
import json
import math
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DB = os.path.join(DATA, "demo.db")
RULES = os.path.join(ROOT, "rules", "rules.json")
CANDIDATES = os.path.join(ROOT, "rules", "candidates.json")
GT = os.path.join(DATA, "ground_truth.json")
FEEDBACK = os.path.join(DATA, "feedback.json")
REPORTS = os.path.join(ROOT, "reports")
REPORT_MD = os.path.join(REPORTS, "latest.md")
REPORT_JSON = os.path.join(REPORTS, "latest.json")
REPORT_HTML = os.path.join(REPORTS, "latest.html")
HISTORY = os.path.join(DATA, "history.jsonl")

SEVERITY_ORDER = {"P0": 3, "P1": 2, "P2": 1}


def connect(db=DB):
    if str(db).lower().endswith(".duckdb"):
        import duckdb  # 可选依赖，仅指定 .duckdb 时需要：pip install duckdb
        return duckdb.connect(str(db))
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


def is_duckdb(conn):
    return conn.__class__.__module__.split(".")[0] in ("duckdb", "_duckdb")


def list_tables(conn):
    if is_duckdb(conn):
        return [r[0] for r in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main' ORDER BY table_name"
        ).fetchall()]
    return [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()]


def load_rules():
    with open(RULES, encoding="utf-8") as f:
        return json.load(f)


def load_feedback():
    if not os.path.exists(FEEDBACK):
        return {"records": []}
    with open(FEEDBACK, encoding="utf-8") as f:
        return json.load(f)


def save_feedback(fb):
    os.makedirs(DATA, exist_ok=True)
    with open(FEEDBACK, "w", encoding="utf-8") as f:
        json.dump(fb, f, ensure_ascii=False, indent=2)


def is_suppressed(table, rowid, rule, fb):
    for rec in fb.get("records", []):
        if rec["table"] != table:
            continue
        if int(rec["rowid"]) != int(rowid):
            continue
        if rec["rule"] in ("*", rule):
            return True
    return False


def _rows(cur):
    """把游标结果转成 dict 列表（兼容 sqlite3.Row 与 duckdb tuple）。"""
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


def _columns(conn, table):
    return _rows(conn.execute(f"PRAGMA table_info('{table}')"))


def table_rows(conn, table):
    if is_duckdb(conn):
        cols = [c["name"] for c in _columns(conn, table)]
        sel = "__dq_rid__ AS __rowid__, *" if "__dq_rid__" in cols else "rowid AS __rowid__, *"
    else:
        sel = "rowid AS __rowid__, *"
    return _rows(conn.execute(f"SELECT {sel} FROM {table}"))


def check_rule(conn, table, rule):
    """返回违规行列表。"""
    t = rule["type"]
    col = rule.get("column")
    rows = table_rows(conn, table)
    bad = []

    if t == "not_null":
        for r in rows:
            v = r.get(col)
            if v is None or (isinstance(v, str) and v.strip() == ""):
                bad.append(r)

    elif t == "unique":
        cols = rule["columns"]
        groups = {}
        for r in rows:
            key = tuple(r.get(c) for c in cols)
            if any(k is None for k in key):
                continue
            groups.setdefault(key, []).append(r)
        for lst in groups.values():
            if len(lst) > 1:
                bad.extend(lst)

    elif t == "range":
        lo, hi = rule.get("min"), rule.get("max")
        for r in rows:
            v = r.get(col)
            if v is None:
                continue
            try:
                fv = float(v)
            except (TypeError, ValueError):
                bad.append(r)
                continue
            if (lo is not None and fv < lo) or (hi is not None and fv > hi):
                bad.append(r)

    elif t == "regex":
        pat = re.compile(rule["pattern"])
        for r in rows:
            v = r.get(col)
            if v is None or not pat.fullmatch(str(v).strip()):
                bad.append(r)

    elif t == "enum":
        allowed = set(rule["values"])
        for r in rows:
            v = r.get(col)
            if v is None or v not in allowed:
                bad.append(r)

    elif t == "foreign_key":
        ref_table = rule["ref_table"]
        ref_col = rule.get("ref_column", "id")
        valid = {r[0] for r in conn.execute(f"SELECT {ref_col} FROM {ref_table}").fetchall()}
        for r in rows:
            v = r.get(col)
            if v is None:
                continue
            if v not in valid:
                bad.append(r)

    elif t == "freshness":
        max_age = rule.get("max_age_days", 7)
        cutoff = (datetime.now() - timedelta(days=max_age)).strftime("%Y-%m-%d %H:%M:%S")
        for r in rows:
            v = r.get(col)
            if v is None:
                continue
            if str(v) < cutoff:
                bad.append(r)

    elif t == "expression":
        sql = rule["violation_sql"]
        if is_duckdb(conn):
            sql = sql.replace("date('now','localtime')", "CAST(current_date AS VARCHAR)")
        ids = [r[0] for r in conn.execute(sql).fetchall()]
        if is_duckdb(conn) and rows and "__dq_rid__" in rows[0]:
            mapping = dict(conn.execute(f"SELECT rowid, __dq_rid__ FROM {table}").fetchall())
            bad_ids = {mapping[i] for i in ids if i in mapping}
        else:
            bad_ids = set(ids)
        bad = [r for r in rows if r["__rowid__"] in bad_ids]

    else:
        raise ValueError(f"未知规则类型: {t}")

    return bad


def run_all(conn, apply_feedback=True):
    rules = load_rules()
    fb = load_feedback() if apply_feedback else {"records": []}
    results = []
    for table, items in rules.items():
        total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for rule in items:
            bad = check_rule(conn, table, rule)
            suppressed = 0
            kept = []
            for r in bad:
                if is_suppressed(table, r["__rowid__"], rule["name"], fb):
                    suppressed += 1
                else:
                    kept.append(r)
            samples = []
            for r in kept[:5]:
                keep = {k: v for k, v in r.items() if k != "__rowid__"}
                samples.append({"rowid": r["__rowid__"], "values": keep})
            results.append({
                "rule": rule["name"],
                "table": table,
                "type": rule["type"],
                "severity": rule.get("severity", "P2"),
                "checked": total,
                "violations": len(kept),
                "suppressed": suppressed,
                "rowids": [r["__rowid__"] for r in kept],
                "samples": samples,
            })
    return results


def profile(conn):
    out = {}
    for table in list_tables(conn):
        cols = [c for c in _columns(conn, table) if not c["name"].startswith("__")]
        total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        col_stats = []
        for c in cols:
            name = c["name"]
            nulls = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {name} IS NULL OR TRIM(CAST({name} AS VARCHAR))=''"
            ).fetchone()[0]
            distinct = conn.execute(f"SELECT COUNT(DISTINCT {name}) FROM {table}").fetchone()[0]
            try:
                mn, mx = conn.execute(f"SELECT MIN({name}), MAX({name}) FROM {table}").fetchone()
            except Exception:  # noqa: BLE001 - 不同后端异常类型不同
                mn, mx = None, None
            top = conn.execute(
                f"SELECT {name}, COUNT(*) c FROM {table} GROUP BY {name} ORDER BY c DESC LIMIT 3"
            ).fetchall()
            col_stats.append({
                "column": name,
                "null_rate": round(nulls / total, 4) if total else None,
                "distinct": distinct,
                "min": mn,
                "max": mx,
                "top": [{"value": str(r[0]), "count": r[1]} for r in top],
            })
        out[table] = {"rows": total, "columns": col_stats}
    return out


def evaluate(results, gt_path=GT):
    with open(gt_path, encoding="utf-8") as f:
        gt = json.load(f)["rows"]
    gt_rows = {(g["table"], g["rowid"]) for g in gt}

    flagged = set()
    for r in results:
        for rid in r["rowids"]:
            flagged.add((r["table"], rid))

    tp = len(flagged & gt_rows)
    fp = len(flagged - gt_rows)
    fn = len(gt_rows - flagged)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    missed = [g for g in gt if (g["table"], g["rowid"]) not in flagged]

    by_issue = {}
    for g in gt:
        stat = by_issue.setdefault(g["issue"], {"total": 0, "hit": 0})
        stat["total"] += 1
        if (g["table"], g["rowid"]) in flagged:
            stat["hit"] += 1

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "missed": missed,
        "by_issue": by_issue,
    }


def severity_counts(results):
    counts = {"P0": 0, "P1": 0, "P2": 0}
    for r in results:
        counts[r["severity"]] = counts.get(r["severity"], 0) + r["violations"]
    return counts


def gate_exit(sev, cov, fail_on=None, min_coverage=None):
    """返回门禁退出码：P0 违规或覆盖率不达标 → 1。"""
    code = 0
    if fail_on in SEVERITY_ORDER and sev.get(fail_on, 0) > 0:
        code = 1
    if min_coverage is not None and cov and cov["rate"] < min_coverage:
        code = 1
    return code


def _key_fields(conn):
    """关键字段：主键、外键、时间、电话/邮箱、数值、低基数文本。"""
    out = {}
    for table in list_tables(conn):
        cols = [c for c in _columns(conn, table) if not c["name"].startswith("__")]
        total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        keys = []
        for c in cols:
            name = c["name"]
            decl = (c["type"] or "").upper()
            low = name.lower()
            if (name == "id" or low.endswith("_id")
                    or any(k in low for k in ("date", "time", "_at"))
                    or "phone" in low or "email" in low):
                keys.append(name)
                continue
            if decl in ("REAL", "INTEGER", "NUMERIC", "FLOAT", "DOUBLE",
                        "BIGINT", "SMALLINT", "TINYINT", "HUGEINT", "DECIMAL"):
                keys.append(name)
                continue
            if decl in ("TEXT", "STRING", "VARCHAR") and total:
                distinct = conn.execute(f"SELECT COUNT(DISTINCT {name}) FROM {table}").fetchone()[0]
                if distinct <= 20:
                    keys.append(name)
        out[table] = keys
    return out


def coverage(conn):
    """规则覆盖率：被至少一条规则覆盖的关键字段占比。"""
    kf = _key_fields(conn)
    rules = load_rules()
    covered = {}
    for table, items in rules.items():
        cols = [c["name"] for c in _columns(conn, table)]
        cov = set()
        for r in items:
            if r.get("column"):
                cov.add(r["column"])
            for c in r.get("columns", []):
                cov.add(c)
            if r["type"] == "expression":
                for c in cols:
                    if re.search(r"\b" + re.escape(c) + r"\b", r.get("violation_sql", "")):
                        cov.add(c)
        covered[table] = cov
    total = sum(len(v) for v in kf.values())
    hit = sum(len(set(kf[t]) & covered.get(t, set())) for t in kf)
    uncovered = {
        t: [c for c in kf[t] if c not in covered.get(t, set())]
        for t in kf if set(kf[t]) - covered.get(t, set())
    }
    return {
        "total": total,
        "covered": hit,
        "rate": round(hit / total, 4) if total else 1.0,
        "uncovered": uncovered,
    }


def _fmt_metric(v):
    return f"{v * 100:.1f}%"


def record_history(results, metrics, cov):
    os.makedirs(DATA, exist_ok=True)
    sev = severity_counts(results)
    row = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rules": len(results),
        "violations": sum(r["violations"] for r in results),
        "p0": sev["P0"], "p1": sev["P1"], "p2": sev["P2"],
        "suppressed": sum(r["suppressed"] for r in results),
        "recall": metrics["recall"] if metrics else None,
        "precision": metrics["precision"] if metrics else None,
        "coverage": cov["rate"] if cov else None,
    }
    with open(HISTORY, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def build_report(results, metrics=None, cov=None, db_path=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db_path = db_path or DB
    lines = ["# 数据质量巡检报告", ""]
    lines.append(f"- 生成时间：{now}")
    lines.append(f"- 数据库：`{db_path}`")
    lines.append(f"- 规则数：{len(results)}")
    lines.append(f"- 已标注误报（抑制）：{sum(r['suppressed'] for r in results)} 条")
    lines.append("")

    total_violations = sum(r["violations"] for r in results)
    sev = severity_counts(results)

    lines.append("## 一、总览")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("| --- | --- |")
    lines.append(f"| 违规行数（含重复计数） | {total_violations} |")
    lines.append(f"| P0 违规 | {sev.get('P0', 0)} |")
    lines.append(f"| P1 违规 | {sev.get('P1', 0)} |")
    lines.append(f"| P2 违规 | {sev.get('P2', 0)} |")
    if cov:
        lines.append(f"| 规则覆盖率 | {_fmt_metric(cov['rate'])}（{cov['covered']}/{cov['total']} 关键字段） |")
    if metrics:
        lines.append(f"| 检出率（Recall） | {_fmt_metric(metrics['recall'])} |")
        lines.append(f"| 误报率（1 - Precision） | {_fmt_metric(1 - metrics['precision'])} |")
        lines.append(f"| F1 | {metrics['f1']:.4f} |")
    lines.append("")
    if cov and cov.get("uncovered"):
        parts = "；".join(f"{t}：{', '.join(cs)}" for t, cs in cov["uncovered"].items())
        lines.append(f"> 未覆盖的关键字段——{parts}")
        lines.append("")

    lines.append("## 二、规则结果")
    lines.append("")
    lines.append("| 规则 | 表 | 级别 | 检查行数 | 违规行数 | 已抑制 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for r in results:
        lines.append(
            f"| {r['rule']} | {r['table']} | {r['severity']} | {r['checked']} | {r['violations']} | {r['suppressed']} |"
        )
    lines.append("")

    lines.append("## 三、违规明细（每规则前 5 条）")
    lines.append("")
    for r in results:
        if not r["violations"]:
            continue
        lines.append(f"### {r['rule']}")
        lines.append("")
        lines.append("| rowid | 值 |")
        lines.append("| --- | --- |")
        for s in r["samples"]:
            vals = ", ".join(f"{k}={v}" for k, v in s["values"].items())
            lines.append(f"| {s['rowid']} | {vals} |")
        lines.append("")

    if metrics:
        lines.append("## 四、评测（与 ground truth 对比）")
        lines.append("")
        lines.append("| 指标 | 值 |")
        lines.append("| --- | --- |")
        lines.append(f"| TP | {metrics['tp']} |")
        lines.append(f"| FP | {metrics['fp']} |")
        lines.append(f"| FN | {metrics['fn']} |")
        lines.append(f"| 检出率 | {_fmt_metric(metrics['recall'])} |")
        lines.append(f"| 误报率 | {_fmt_metric(1 - metrics['precision'])} |")
        lines.append("")
        if metrics["missed"]:
            lines.append("漏报明细：")
            lines.append("")
            for m in metrics["missed"]:
                lines.append(f"- {m['table']} rowid={m['rowid']}：{m['issue']}")
            lines.append("")

    lines.append("## 五、修复建议")
    lines.append("")
    for r in results:
        if not r["violations"]:
            continue
        if r["type"] == "not_null":
            lines.append(f"- **{r['rule']}**：定位空值来源，补默认值或在入仓前过滤；必要时在 ETL 加非空校验。")
        elif r["type"] == "unique":
            lines.append(f"- **{r['rule']}**：确认是否重复写入（幂等问题），按业务键去重并加唯一约束。")
        elif r["type"] == "range":
            lines.append(f"- **{r['rule']}**：检查上游单位/精度/数据口径，修正后加范围校验。")
        elif r["type"] == "regex":
            lines.append(f"- **{r['rule']}**：统一清洗规则（去空格、正则替换），并抽样复核。")
        elif r["type"] == "enum":
            lines.append(f"- **{r['rule']}**：补充维表映射，未知值转“其他”并登记。")
        elif r["type"] == "foreign_key":
            lines.append(f"- **{r['rule']}**：补维表或修正关联键；入仓前做孤儿键检查。")
        elif r["type"] == "freshness":
            lines.append(f"- **{r['rule']}**：检查调度依赖与分区产出，恢复后补跑；对延迟加告警。")
        elif r["type"] == "expression":
            lines.append(f"- **{r['rule']}**：按表达式定位计算逻辑，修正后回归验证。")
    lines.append("")

    return "\n".join(lines)


def write_report(results, metrics=None, cov=None, db_path=None):
    os.makedirs(REPORTS, exist_ok=True)
    md = build_report(results, metrics, cov, db_path)
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump({"results": results, "metrics": metrics, "coverage": cov}, f,
                  ensure_ascii=False, indent=2)
    with open(REPORT_HTML, "w", encoding="utf-8") as f:
        f.write(build_html_report(results, metrics, cov, db_path))
    record_history(results, metrics, cov)
    return REPORT_MD


def _sparkline(values, color="#c0392b", width=560, height=70):
    if not values:
        return ""
    n = len(values)
    mx, mn = max(values), min(values)
    pts = []
    for i, v in enumerate(values):
        x = 12 + (width - 24) * (i / (n - 1) if n > 1 else 0.5)
        ratio = (v - mn) / (mx - mn) if mx > mn else 0.5
        y = height - 8 - (height - 16) * ratio
        pts.append(f"{x:.1f},{y:.1f}")
    return (f'<polyline fill="none" stroke="{color}" stroke-width="2" '
            f'points="{" ".join(pts)}"/>')


def build_html_report(results, metrics=None, cov=None, db_path=None):
    from html import escape

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db_path = db_path or DB
    sev = severity_counts(results)
    total_violations = sum(r["violations"] for r in results)

    hist = []
    if os.path.exists(HISTORY):
        with open(HISTORY, encoding="utf-8") as f:
            hist = [json.loads(line) for line in f if line.strip()][-20:]

    cards = [
        ("P0", sev.get("P0", 0), "bad"),
        ("P1", sev.get("P1", 0), "warn"),
        ("P2", sev.get("P2", 0), "info"),
        ("规则覆盖率", f"{cov['rate']*100:.1f}%" if cov else "-", "good"),
        ("检出率", f"{metrics['recall']*100:.1f}%" if metrics else "-", "good"),
        ("误报率", f"{(1-metrics['precision'])*100:.1f}%" if metrics else "-", "good"),
    ]
    card_html = "".join(
        f'<div class="card {cls}"><div class="k">{escape(k)}</div><div class="v">{v}</div></div>'
        for k, v, cls in cards
    )

    rows = []
    for r in results:
        cls = {"P0": "bad", "P1": "warn", "P2": "info"}.get(r["severity"], "")
        rows.append(
            f'<tr><td>{escape(r["rule"])}</td><td>{r["table"]}</td>'
            f'<td><span class="tag {cls}">{r["severity"]}</span></td>'
            f'<td>{r["checked"]}</td><td>{r["violations"]}</td><td>{r["suppressed"]}</td></tr>'
        )

    details = []
    for r in results:
        if not r["violations"]:
            continue
        sample_rows = "".join(
            f'<tr><td>{s["rowid"]}</td><td><code>{escape(", ".join(f"{k}={v}" for k, v in list(s["values"].items())[:4]))}</code></td></tr>'
            for s in r["samples"]
        )
        details.append(
            f'<h3>{escape(r["rule"])}</h3><table class="mini"><tr><th>rowid</th><th>样例</th></tr>{sample_rows}</table>'
        )

    trend = ""
    if hist:
        viol = [h["violations"] for h in hist]
        covs = [h["coverage"] * 100 for h in hist if h.get("coverage") is not None]
        vmin, vmax = min(viol), max(viol)
        cmin, cmax = (min(covs), max(covs)) if covs else (0, 100)
        trend = (
            '<div class="trend">'
            f'<div class="legend"><span class="dot red"></span>违规行数（{vmin}–{vmax}）</div>'
            f'<svg viewBox="0 0 560 60" preserveAspectRatio="none">'
            f'{_sparkline(viol, "#c0392b", 560, 60)}</svg>'
            f'<div class="legend"><span class="dot blue"></span>覆盖率 %（{cmin:.0f}–{cmax:.0f}）</div>'
            f'<svg viewBox="0 0 560 60" preserveAspectRatio="none">'
            f'{_sparkline(covs, "#2E74B5", 560, 60)}</svg>'
            '</div>'
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>数据质量巡检报告</title>
<style>
:root {{ --navy:#1F4E79; --bad:#c0392b; --warn:#d68910; --info:#2E74B5; --good:#1e8449; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; padding:32px 40px; font-family:"Microsoft YaHei","Segoe UI",sans-serif; color:#262626; background:#fafbfc; }}
h1 {{ color:var(--navy); margin:0 0 6px; font-size:26px; }}
.meta {{ color:#666; font-size:13px; margin-bottom:18px; }}
.cards {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:18px; }}
.card {{ background:#fff; border:1px solid #e3e8ef; border-radius:10px; padding:12px 16px; min-width:120px; box-shadow:0 1px 2px rgba(0,0,0,.04); }}
.card .k {{ color:#666; font-size:12px; }}
.card .v {{ font-size:24px; font-weight:700; color:var(--navy); }}
.card.bad .v {{ color:var(--bad); }} .card.warn .v {{ color:var(--warn); }} .card.good .v {{ color:var(--good); }}
table {{ border-collapse:collapse; width:100%; background:#fff; border:1px solid #e3e8ef; border-radius:8px; overflow:hidden; margin-bottom:20px; }}
th, td {{ padding:8px 10px; border-bottom:1px solid #eef1f5; font-size:13px; text-align:left; }}
th {{ background:#f4f7fb; color:#445; }}
h2 {{ color:var(--navy); font-size:18px; margin:22px 0 10px; }}
h3 {{ font-size:14px; margin:16px 0 6px; color:#333; }}
.tag {{ padding:1px 8px; border-radius:10px; font-size:12px; color:#fff; }}
.tag.bad {{ background:var(--bad); }} .tag.warn {{ background:var(--warn); }} .tag.info {{ background:var(--info); }}
.trend {{ background:#fff; border:1px solid #e3e8ef; border-radius:8px; padding:12px 16px; margin-bottom:16px; }}
.trend svg {{ width:100%; height:60px; display:block; margin-bottom:8px; }}
.legend {{ font-size:12px; color:#666; margin-bottom:6px; }}
.dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin:0 4px 0 12px; }}
.dot.red {{ background:var(--bad); }} .dot.blue {{ background:var(--info); }}
code {{ background:#f4f6f8; padding:1px 5px; border-radius:4px; font-size:12px; }}
</style></head><body>
<h1>数据质量巡检报告</h1>
<div class="meta">生成时间：{now} ｜ 数据库：{escape(str(db_path))} ｜ 规则数：{len(results)} ｜ 违规：{total_violations}（含重复计数）</div>
<div class="cards">{card_html}</div>
<h2>趋势（最近 {len(hist)} 次）</h2>{trend}
<h2>规则结果</h2>
<table><tr><th>规则</th><th>表</th><th>级别</th><th>检查行数</th><th>违规</th><th>已抑制</th></tr>{''.join(rows)}</table>
<h2>违规明细</h2>{''.join(details)}
</body></html>"""


# ---------------------------------------------------------------- suggest
def _quantile(conn, table, col, q):
    total = conn.execute(f"SELECT COUNT({col}) FROM {table}").fetchone()[0]
    if not total:
        return None
    offset = max(0, int(total * q) - 1)
    row = conn.execute(
        f"SELECT {col} FROM {table} WHERE {col} IS NOT NULL ORDER BY {col} LIMIT 1 OFFSET ?",
        (offset,),
    ).fetchone()
    return row[0] if row else None


def _table_names(conn):
    return list_tables(conn)


def _rule(table, name, rtype, severity, **kw):
    rule = {"name": f"{table}.{name}", "type": rtype, "severity": severity}
    rule.update(kw)
    return rule


def suggest_rules(conn):
    """基于画像生成候选规则（启发式，需人工确认）。"""
    tables = _table_names(conn)
    existing = set()
    try:
        for _, items in load_rules().items():
            for r in items:
                existing.add(r["name"])
    except FileNotFoundError:
        pass

    candidates = []

    def add(rule, basis):
        if any(c["name"] == rule["name"] for c in candidates):
            return
        rule["design_basis"] = basis
        rule["already_exists"] = rule["name"] in existing
        candidates.append(rule)

    for table in tables:
        cols = [c for c in _columns(conn, table) if not c["name"].startswith("__")]
        total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for c in cols:
            name = c["name"]
            decl = (c["type"] or "").upper()
            low = name.lower()

            if name == "id":
                add(_rule(table, "id 非空", "not_null", "P0", column="id"), "主键/业务键不能为空")
                add(_rule(table, "id 唯一", "unique", "P0", columns=["id"]), "主键/业务键不能重复")
                continue

            if low.endswith("_id"):
                ref = low[:-3] + "s"
                if ref in tables:
                    add(_rule(table, f"{name} 外键", "foreign_key", "P0",
                              column=name, ref_table=ref, ref_column="id"),
                        f"{name} 应能在 {ref}.id 中找到")
                else:
                    add(_rule(table, f"{name} 非空", "not_null", "P1", column=name),
                        "关联键不应为空")
                continue

            if "phone" in low:
                add(_rule(table, f"{name} 手机号格式", "regex", "P1", column=name,
                          pattern="^1[3-9]\\d{9}$"), "中国大陆手机号 11 位，1 开头")
                continue

            if "email" in low:
                add(_rule(table, f"{name} 邮箱格式", "regex", "P1", column=name,
                          pattern="^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$"), "邮箱需含 @ 与域名后缀")
                continue

            if any(k in low for k in ("date", "time", "signup", "created", "_at")):
                add(_rule(table, f"{name} 非空", "not_null", "P1", column=name), "时间字段不应为空")
                add(_rule(table, f"{name} 新鲜度（7 天）", "freshness", "P1",
                          column=name, max_age_days=7), "分区数据不应超过 7 天未更新")
                continue

            if decl in ("REAL", "INTEGER", "NUMERIC", "FLOAT", "DOUBLE",
                        "BIGINT", "SMALLINT", "TINYINT", "HUGEINT", "DECIMAL"):
                q1 = _quantile(conn, table, name, 0.01)
                q99 = _quantile(conn, table, name, 0.99)
                if q1 is not None and q99 is not None and q99 > q1:
                    lo = min(0, math.floor(q1)) if q1 < 0 else 0
                    hi = math.ceil(q99 * 1.2)
                    add(_rule(table, f"{name} 范围", "range", "P2",
                              column=name, min=lo, max=hi),
                        f"按 1%/99% 分位放宽到 [{lo}, {hi}]，排除离群值")
                continue

            if decl == "TEXT" and total:
                vals = [r[0] for r in conn.execute(
                    f"SELECT DISTINCT {name} FROM {table} WHERE {name} IS NOT NULL"
                ).fetchall()]
                if 0 < len(vals) <= 12:
                    vals = sorted(str(v) for v in vals)
                    add(_rule(table, f"{name} 枚举", "enum", "P2", column=name, values=vals),
                        f"当前取值 {len(vals)} 种，适合做枚举白名单")

    return candidates


def llm_refine(candidates):
    """可选：调用 OpenAI 兼容接口润色候选规则。未配置时原样返回。"""
    base = os.environ.get("DQ_LLM_BASE", "").rstrip("/")
    key = os.environ.get("DQ_LLM_KEY", "")
    model = os.environ.get("DQ_LLM_MODEL", "gpt-4o-mini")
    if not base or not key:
        print("[suggest] 未配置 DQ_LLM_BASE / DQ_LLM_KEY，跳过 LLM，使用启发式结果。")
        return candidates, "heuristic"

    import urllib.request

    prompt = (
        "你是数据质量专家。下面是启发式生成的候选规则（JSON）。"
        "请检查字段类型与规则是否匹配，补充可能遗漏的规则，"
        "输出 JSON 数组，每项包含 name/type/severity/参数/design_basis。只输出 JSON。\n"
        + json.dumps(candidates, ensure_ascii=False)
    )
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"].strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text[text.find("["):]
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed, "llm"
    except Exception as exc:  # noqa: BLE001
        print(f"[suggest] LLM 调用失败，回退启发式：{exc}")
    return candidates, "heuristic(fallback)"


# ---------------------------------------------------------------- commands
def cmd_init(args):
    import make_demo
    db, gt, manifest = make_demo.build(dirty=not getattr(args, "clean", False))
    print(f"已生成演示库：{db}")
    if manifest:
        print(f"注入问题：{len(manifest)} 条（ground truth 已写入 {GT}）")
    else:
        print("干净数据：未注入脏数据（用于 CI 门禁基线）")


def cmd_check(args):
    if args.min_coverage is not None and not (0 <= args.min_coverage <= 1):
        print("::error::--min-coverage 需在 0~1 之间")
        return 2
    conn = connect(args.db)
    results = run_all(conn)
    metrics = evaluate(results) if os.path.exists(GT) else None
    cov = coverage(conn)
    path = write_report(results, metrics, cov, db_path=args.db)
    sev = severity_counts(results)
    total = sum(r["violations"] for r in results)
    print(f"规则 {len(results)} 条，违规 {total} 行（P0={sev['P0']} / P1={sev['P1']} / P2={sev['P2']}），"
          f"已抑制 {sum(r['suppressed'] for r in results)} 条")
    print(f"规则覆盖率 {cov['rate']*100:.1f}%（{cov['covered']}/{cov['total']} 关键字段）")
    if metrics:
        print(f"检出率 {metrics['recall']*100:.1f}%，误报率 {(1-metrics['precision'])*100:.1f}%")
    print(f"报告：{path}")

    fail_on = args.fail_on
    min_cov = args.min_coverage
    if fail_on in SEVERITY_ORDER and sev.get(fail_on, 0) > 0:
        print(f"::error::{fail_on} 违规 {sev[fail_on]} 条，门禁未通过")
    if min_cov is not None and cov["rate"] < min_cov:
        print(f"::error::规则覆盖率 {cov['rate']*100:.1f}% 低于阈值 {min_cov*100:.1f}%")
    return gate_exit(sev, cov, fail_on, min_cov)


def cmd_profile(args):
    conn = connect(args.db)
    print(json.dumps(profile(conn), ensure_ascii=False, indent=2))


def cmd_evaluate(args):
    conn = connect(args.db)
    results = run_all(conn)
    print(json.dumps(evaluate(results), ensure_ascii=False, indent=2))


def cmd_demo(_args):
    import make_demo
    make_demo.build()
    conn = connect()
    results = run_all(conn)
    metrics = evaluate(results)
    cov = coverage(conn)
    path = write_report(results, metrics, cov)
    sev = severity_counts(results)
    print("== dq-sentinel demo ==")
    print("表：users / products / orders")
    print(f"规则 {len(results)} 条，违规 {sum(r['violations'] for r in results)} 行"
          f"（P0={sev['P0']} / P1={sev['P1']} / P2={sev['P2']}）")
    print(f"规则覆盖率 {cov['rate']*100:.1f}%（{cov['covered']}/{cov['total']} 关键字段）")
    print(f"检出率 {metrics['recall']*100:.1f}%，误报率 {(1-metrics['precision'])*100:.1f}%，F1 {metrics['f1']:.4f}")
    print(f"报告已写入：{path}")


def cmd_history(_args):
    if not os.path.exists(HISTORY):
        print("暂无历史记录（先运行 demo 或 check）")
        return
    print(f"{'时间':<20} {'规则':>4} {'违规':>4} {'P0':>3} {'P1':>3} {'P2':>3} {'检出率':>7} {'覆盖率':>7}")
    with open(HISTORY, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            rec = "-" if row["recall"] is None else f"{row['recall']*100:.1f}%"
            cov = "-" if row["coverage"] is None else f"{row['coverage']*100:.1f}%"
            print(f"{row['time']:<20} {row['rules']:>4} {row['violations']:>4} "
                  f"{row['p0']:>3} {row['p1']:>3} {row['p2']:>3} {rec:>7} {cov:>7}")


def cmd_mark(args):
    fb = load_feedback()
    fb.setdefault("records", []).append({
        "table": args.table,
        "rowid": int(args.rowid),
        "rule": args.rule,
        "reason": args.reason,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_feedback(fb)
    print(f"已标注误报：{args.table} rowid={args.rowid} rule={args.rule}（原因：{args.reason}）")


def cmd_unmark(args):
    fb = load_feedback()
    before = len(fb.get("records", []))
    fb["records"] = [r for r in fb.get("records", [])
                     if not (r["table"] == args.table and int(r["rowid"]) == int(args.rowid)
                             and r["rule"] == args.rule)]
    save_feedback(fb)
    print(f"已移除标注 {before - len(fb['records'])} 条")


def cmd_suggest(args):
    conn = connect(args.db)
    candidates = suggest_rules(conn)
    source = "heuristic"
    if args.llm:
        candidates, source = llm_refine(candidates)
    os.makedirs(os.path.dirname(CANDIDATES), exist_ok=True)
    with open(CANDIDATES, "w", encoding="utf-8") as f:
        json.dump({"source": source, "candidates": candidates}, f, ensure_ascii=False, indent=2)
    new_count = sum(1 for c in candidates if not c.get("already_exists"))
    print(f"候选规则 {len(candidates)} 条（其中新增 {new_count} 条；来源：{source}）")
    print(f"已写入：{CANDIDATES}")
    print("请人工确认后合并到 rules/rules.json")


def main():
    parser = argparse.ArgumentParser(description="数据质量巡检 Agent Skill")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--clean", action="store_true", help="不注入脏数据（CI 基线）")
    p_init.set_defaults(func=cmd_init)

    p_check = sub.add_parser("check")
    p_check.add_argument("--db", default=DB, help="数据库路径（.duckdb 需安装 duckdb）")
    p_check.add_argument("--fail-on", choices=["P0", "P1", "P2"], default=None,
                         help="指定级别有违规时退出码 1（CI 门禁）")
    p_check.add_argument("--min-coverage", type=float, default=None,
                         help="规则覆盖率阈值（0-1），低于阈值时退出码 1")
    p_check.set_defaults(func=cmd_check)

    p_profile = sub.add_parser("profile")
    p_profile.add_argument("--db", default=DB)
    p_profile.set_defaults(func=cmd_profile)

    p_evaluate = sub.add_parser("evaluate")
    p_evaluate.add_argument("--db", default=DB)
    p_evaluate.set_defaults(func=cmd_evaluate)

    sub.add_parser("demo").set_defaults(func=cmd_demo)
    sub.add_parser("history").set_defaults(func=cmd_history)

    p_mark = sub.add_parser("mark", help="标注误报（规则误报）")
    p_mark.add_argument("--table", required=True)
    p_mark.add_argument("--rowid", required=True)
    p_mark.add_argument("--rule", default="*", help="规则名，默认 * 表示该行全部规则")
    p_mark.add_argument("--reason", default="")
    p_mark.set_defaults(func=cmd_mark)

    p_unmark = sub.add_parser("unmark", help="移除误报标注")
    p_unmark.add_argument("--table", required=True)
    p_unmark.add_argument("--rowid", required=True)
    p_unmark.add_argument("--rule", default="*")
    p_unmark.set_defaults(func=cmd_unmark)

    p_suggest = sub.add_parser("suggest", help="生成候选规则")
    p_suggest.add_argument("--db", default=DB)
    p_suggest.add_argument("--llm", action="store_true", help="尝试调用 LLM 润色")
    p_suggest.set_defaults(func=cmd_suggest)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
