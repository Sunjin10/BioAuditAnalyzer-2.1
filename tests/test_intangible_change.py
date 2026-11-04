import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.intangible_change import analyze_intangible_change
from scripts.run_int02 import update_report, START, END


def make_raw(current, previous, assets):
    """테스트용 가상 재무상태표"""

    return pd.DataFrame([
        {
            "sj_div": "BS",
            "account_id": (
                "ifrs-full_IntangibleAssetsAndGoodwill"
            ),
            "thstrm_amount": str(current),
            "frmtrm_amount": str(previous)
        },
        {
            "sj_div": "BS",
            "account_id": "ifrs-full_Assets",
            "thstrm_amount": str(assets),
            "frmtrm_amount": str(assets)
        }
    ])


class TestIntangibleChange(unittest.TestCase):

    def test_01_both_signals(self):
        """비중과 증가 조건을 모두 충족"""

        raw = make_raw(
            current=32_000_000_000,
            previous=20_000_000_000,
            assets=200_000_000_000
        )

        result = analyze_intangible_change(raw)

        self.assertTrue(result["int01"])
        self.assertTrue(result["int02"])

    def test_02_exact_threshold(self):
        """증가액 100억 및 증가율 5% 경계값"""

        raw = make_raw(
            current=210_000_000_000,
            previous=200_000_000_000,
            assets=2_000_000_000_000
        )

        result = analyze_intangible_change(raw)

        self.assertFalse(result["int01"])
        self.assertTrue(result["int02"])

    def test_03_amount_below_threshold(self):
        """증가율이 높아도 증가액이 100억 미만"""

        raw = make_raw(
            current=109_000_000_000,
            previous=100_000_000_000,
            assets=1_000_000_000_000
        )

        result = analyze_intangible_change(raw)

        self.assertFalse(result["int02"])

    def test_04_rate_below_threshold(self):
        """증가액이 100억이어도 증가율이 5% 미만"""

        raw = make_raw(
            current=410_000_000_000,
            previous=400_000_000_000,
            assets=2_000_000_000_000
        )

        result = analyze_intangible_change(raw)

        self.assertFalse(result["int02"])

    def test_05_zero_previous_balance(self):
        """전기 금액이 0일 때 증가율 계산 불가"""

        raw = make_raw(
            current=20_000_000_000,
            previous=0,
            assets=200_000_000_000
        )

        result = analyze_intangible_change(raw)

        self.assertIsNone(result["change_rate"])
        self.assertFalse(result["int02"])

    def test_06_report_not_duplicated(self):
        """보고서 재실행 시 INT-02 구역 중복 방지"""

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "report.md"

            path.write_text(
                "# 기존 보고서\n",
                encoding="utf-8"
            )

            update_report(path, "첫 번째 분석")
            update_report(path, "수정된 분석")

            content = path.read_text(
                encoding="utf-8"
            )

            self.assertEqual(content.count(START), 1)
            self.assertEqual(content.count(END), 1)
            self.assertIn("수정된 분석", content)
            self.assertNotIn("첫 번째 분석", content)


if __name__ == "__main__":
    unittest.main()
