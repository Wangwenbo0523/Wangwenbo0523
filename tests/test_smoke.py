# -*- coding: utf-8 -*-
"""冒烟测试：演示库、巡检指标、误报标注、CI 门禁、候选规则、DuckDB 后端。"""
import importlib.util
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import dq  # noqa: E402
import make_demo  # noqa: E402

HAS_DUCKDB = importlib.util.find_spec("duckdb") is not None


class DemoSentinelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        make_demo.build()

    def _conn(self, db=dq.DB):
        conn = dq.connect(db)
        self.addCleanup(conn.close)
        return conn

    def test_demo_metrics(self):
        conn = self._conn()
        results = dq.run_all(conn)
        metrics = dq.evaluate(results)
        self.assertGreaterEqual(metrics["recall"], 0.95, "检出率过低")
        self.assertGreaterEqual(metrics["precision"], 0.95, "误报率过高")
        self.assertEqual(len(results), 22, "规则数量应为 22")

    def test_report_written(self):
        conn = self._conn()
        results = dq.run_all(conn)
        metrics = dq.evaluate(results)
        path = dq.write_report(results, metrics)
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as f:
            self.assertIn("数据质量巡检报告", f.read())
        self.assertTrue(os.path.exists(dq.REPORT_HTML))
        with open(dq.REPORT_HTML, encoding="utf-8") as f:
            self.assertIn("数据质量巡检报告", f.read())

    def test_feedback_suppression(self):
        conn = self._conn()
        fb = dq.load_feedback()
        original = list(fb.get("records", []))
        rule_name = "users.phone 手机号格式"
        try:
            dq.save_feedback({"records": original + [{
                "table": "users", "rowid": 7, "rule": rule_name,
                "reason": "测试账号", "time": "2026-10-20 00:00:00",
            }]})
            results = dq.run_all(conn)
            rule = next(r for r in results if r["rule"] == rule_name)
            self.assertEqual(rule["suppressed"], 1)
            self.assertEqual(rule["violations"], 0)
        finally:
            dq.save_feedback({"records": original})

    def test_fail_on_gate(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", "dq.py"), "check", "--fail-on", "P0"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 1, "存在 P0 违规时门禁应失败")
        self.assertIn("门禁未通过", proc.stdout)

    def test_coverage_gate(self):
        sev = {"P0": 0, "P1": 0, "P2": 0}
        self.assertEqual(dq.gate_exit(sev, {"rate": 0.5}, None, 0.8), 1, "覆盖率不达标应失败")
        self.assertEqual(dq.gate_exit(sev, {"rate": 0.9}, None, 0.8), 0, "覆盖率达标应通过")
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", "dq.py"),
             "check", "--min-coverage", "0.99"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, "当前覆盖率 100% 应通过 0.99 阈值")

    def test_suggest_rules(self):
        conn = self._conn()
        candidates = dq.suggest_rules(conn)
        self.assertGreater(len(candidates), 10, "候选规则过少")
        types = {c["type"] for c in candidates}
        self.assertTrue({"not_null", "unique", "foreign_key"} <= types)

    @unittest.skipUnless(HAS_DUCKDB, "需要 duckdb（pip install duckdb）")
    def test_duckdb_backend(self):
        import make_demo_duck
        db = make_demo_duck.build(dirty=True)
        conn = self._conn(db)
        results = dq.run_all(conn)
        metrics = dq.evaluate(results)
        self.assertEqual(len(results), 22)
        self.assertEqual(metrics["recall"], 1.0)
        self.assertEqual(metrics["precision"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
