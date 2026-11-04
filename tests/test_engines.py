
import unittest
import numpy as np
import pandas as pd

from src.risk_engine import (
    detect_signals,
    build_risk_report
)
from src.pbc_engine import build_pbc_report


class TestAuditEngines(unittest.TestCase):

    def setUp(self):
        # 검토 신호가 발생하지 않는 기본 가상 데이터
        self.base = {
            "기업": "테스트기업",
            "매출증가율(%)": 10.0,
            "재고증가율(%)": 10.0,
            "2024년 회전율": 100.0,
            "2025년 회전율": 100.0,
            "무형자산비중(%)": 10.0
        }

    def test_01_exact_thresholds(self):
        # 모든 규칙의 경계값을 정확히 충족
        row = self.base.copy()
        row["매출증가율(%)"] = 50.0
        row["재고증가율(%)"] = 65.0
        row["2025년 회전율"] = 95.0
        row["무형자산비중(%)"] = 15.0

        signals = detect_signals(pd.Series(row))
        rules = {signal["규칙"] for signal in signals}

        self.assertEqual(
            rules,
            {"INV-01", "INV-02", "REV-01", "INT-01"}
        )

    def test_02_below_thresholds(self):
        # 모든 기준값에 조금씩 미달
        row = self.base.copy()
        row["매출증가율(%)"] = 49.99
        row["재고증가율(%)"] = 64.98
        row["2025년 회전율"] = 95.01
        row["무형자산비중(%)"] = 14.99

        signals = detect_signals(pd.Series(row))

        self.assertEqual(len(signals), 0)

    def test_03_missing_values(self):
        # 일부 값이 비어 있을 때
        row = self.base.copy()
        row["매출증가율(%)"] = np.nan
        row["재고증가율(%)"] = np.nan

        signals = detect_signals(pd.Series(row))

        self.assertEqual(len(signals), 0)

    def test_04_empty_report(self):
        # 신호가 없어도 보고서 구조를 유지하는지
        df = pd.DataFrame([self.base])

        report = build_risk_report(df)

        self.assertTrue(report.empty)
        self.assertIn("규칙", report.columns)

    def test_05_duplicate_company(self):
        # 같은 기업이 중복되면 오류 발생
        df = pd.DataFrame([self.base, self.base])

        with self.assertRaises(ValueError):
            build_risk_report(df)

    def test_06_pbc_recommendation(self):
        # 위험 규칙 4개에 PBC 2건씩 추천되는지
        rules = ["INV-01", "INV-02", "REV-01", "INT-01"]

        risk_df = pd.DataFrame([
            {
                "기업": "테스트기업",
                "규칙": rule,
                "검토 신호": "테스트",
                "관련 기준": "테스트"
            }
            for rule in rules
        ])

        result = build_pbc_report(risk_df)

        self.assertEqual(len(result), 8)
        self.assertIn("요청자료", result.columns)
        self.assertIn("검증절차", result.columns)

    def test_07_unknown_rule(self):
        # 정의하지 않은 규칙은 허용하지 않음
        risk_df = pd.DataFrame([{
            "기업": "테스트기업",
            "규칙": "UNKNOWN-01",
            "검토 신호": "테스트",
            "관련 기준": "테스트"
        }])

        with self.assertRaises(ValueError):
            build_pbc_report(risk_df)


if __name__ == "__main__":
    unittest.main()
