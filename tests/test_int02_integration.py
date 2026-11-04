import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.int02_integration import (
    merge_int02,
    RISK_COLUMNS,
    PBC_COLUMNS
)


class TestINT02Integration(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.prefix = "테스트기업_2025_CFS"

        risk = pd.DataFrame([{
            "기업": "테스트기업",
            "사업모델": "mixed",
            "규칙": "INV-02",
            "검토우선순위": "우선 검토",
            "검토 신호": "재고자산회전율 하락",
            "근거": "테스트",
            "관련 기준": "K-IFRS 제1002호"
        }], columns=RISK_COLUMNS)

        pbc = pd.DataFrame([
            {
                "기업": "테스트기업",
                "규칙": "INV-02",
                "검토 신호": "재고자산회전율 하락",
                "관련 기준": "K-IFRS 제1002호",
                "감사주장": "평가",
                "요청자료": f"기존자료 {i}",
                "검증목적": "기존 목적",
                "검증절차": "기존 절차",
                "검토우선순위": "우선 검토",
                "추천유형": "공통",
                "적용조건": "해당 시"
            }
            for i in range(3)
        ], columns=PBC_COLUMNS)

        extra = pd.DataFrame([
            {
                "기업": "테스트기업",
                "규칙": "INT-02",
                "요청자료": f"추가자료 {i}",
                "검증목적": "증가 원인 확인",
                "검증절차": "증빙 대조"
            }
            for i in range(2)
        ])

        risk.to_csv(
            self.folder / f"{self.prefix}_risk.csv",
            index=False
        )

        pbc.to_csv(
            self.folder / f"{self.prefix}_pbc.csv",
            index=False
        )

        extra.to_csv(
            self.folder /
            f"{self.prefix}_intangible_pbc.csv",
            index=False
        )

        self.set_screen(True)

    def tearDown(self):
        self.temp.cleanup()

    def set_screen(self, triggered):
        screen = pd.DataFrame([{
            "기업": "테스트기업",
            "사업연도": 2025,
            "INT-02": "발생" if triggered else "미발생",
            "증감액(원)": 15_000_000_000,
            "증감률(%)": "6.0"
        }])

        screen.to_csv(
            self.folder /
            f"{self.prefix}_intangible_screen.csv",
            index=False
        )

    def run_merge(self):
        return merge_int02(
            "테스트기업",
            2025,
            business_model="mixed",
            output_dir=self.folder
        )

    def test_adds_int02_without_deleting_existing(self):
        risk, pbc = self.run_merge()

        self.assertEqual(len(risk), 2)
        self.assertEqual(len(pbc), 5)

        self.assertEqual(
            risk["규칙"].eq("INV-02").sum(), 1
        )
        self.assertEqual(
            risk["규칙"].eq("INT-02").sum(), 1
        )
        self.assertEqual(
            pbc["규칙"].eq("INV-02").sum(), 3
        )
        self.assertEqual(
            pbc["규칙"].eq("INT-02").sum(), 2
        )

    def test_rerun_does_not_duplicate(self):
        self.run_merge()
        risk, pbc = self.run_merge()

        self.assertEqual(len(risk), 2)
        self.assertEqual(len(pbc), 5)

    def test_signal_disappears_when_not_triggered(self):
        self.run_merge()
        self.set_screen(False)

        risk, pbc = self.run_merge()

        self.assertEqual(len(risk), 1)
        self.assertEqual(len(pbc), 3)
        self.assertNotIn(
            "INT-02", risk["규칙"].tolist()
        )


if __name__ == "__main__":
    unittest.main()
