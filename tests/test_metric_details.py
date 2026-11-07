import unittest

import pandas as pd

from src.financial_metrics import calculate_metrics


class MetricDetailsTests(unittest.TestCase):
    def setUp(self):
        # 실제 공시와 관계없는 가상 금액이며 단위는 원이다.
        self.raw = pd.DataFrame([
            ["IS", "ifrs-full_Revenue", "매출액",
             "80,000,000,000", "50,000,000,000", ""],
            ["IS", "dart_OperatingIncomeLoss", "영업이익",
             "(1,000,000,000)", "100000000", ""],
            ["IS", "ifrs-full_CostOfSales", "매출원가",
             "40000000000", "30000000000", ""],
            ["BS", "ifrs-full_Inventories", "재고자산",
             "30000000000", "10000000000", "5000000000"],
            ["BS", "ifrs-full_Assets", "자산총계",
             "100000000000", "90000000000", ""],
            ["BS", "ifrs-full_Liabilities", "부채총계",
             "30000000000", "20000000000", ""],
            ["BS", "ifrs-full_Equity", "자본총계",
             "70000000000", "70000000000", ""],
            ["BS", "ifrs-full_CurrentAssets", "유동자산",
             "40000000000", "30000000000", ""],
            ["BS", "ifrs-full_CurrentLiabilities", "유동부채",
             "20000000000", "10000000000", ""],
            ["BS", "ifrs-full_IntangibleAssetsAndGoodwill", "무형자산",
             "10000000000", "8000000000", ""],
        ], columns=["sj_div", "account_id", "account_nm",
                    "thstrm_amount", "frmtrm_amount", "bfefrmtrm_amount"])

    def calculate(self):
        return calculate_metrics(
            self.raw, "가상바이오", 2025, "CFS", with_details=True
        )

    def test_details_use_original_amounts_and_preserve_existing_metrics(self):
        metrics, details = self.calculate()
        pd.testing.assert_frame_equal(
            metrics, calculate_metrics(self.raw, "가상바이오", 2025, "CFS")
        )
        self.assertEqual(set(details), set(metrics.columns) -
                         {"기업", "사업연도", "재무제표기준"})
        self.assertEqual(
            details["매출증가율(%)"],
            "(80,000,000,000원 ÷ 50,000,000,000원 − 1) × 100"
        )
        self.assertAlmostEqual(metrics.iloc[0]["매출증가율(%)"], 60)
        self.assertIn("-1,000,000,000원", details["영업이익률(%)"])
        self.assertIn("÷ 2", details["재고자산회전율(회)"])

    def test_missing_comparative_column_has_specific_reason(self):
        self.raw = self.raw.drop(columns="bfefrmtrm_amount")
        metrics, details = self.calculate()
        self.assertTrue(pd.isna(metrics.iloc[0]["전기재고자산회전율(회)"]))
        self.assertEqual(details["전기재고자산회전율(회)"],
                         "전전기 재고자산 금액 없음")
        self.assertEqual(metrics.iloc[0]["재고자산회전율(회)"], 2)

    def test_missing_account_and_empty_value_have_reasons(self):
        self.raw = self.raw[self.raw["account_nm"] != "무형자산"].copy()
        self.raw.loc[self.raw["account_nm"] == "매출액", "frmtrm_amount"] = "-"
        metrics, details = self.calculate()
        self.assertEqual(details["매출증가율(%)"], "전기 매출액 금액 없음")
        self.assertEqual(details["무형자산·영업권비중(%)"],
                         "당기 무형자산 집계액 금액 없음")
        self.assertTrue(pd.isna(metrics.iloc[0]["매출증가율(%)"]))

    def test_zero_and_negative_denominators_have_reasons(self):
        for amount in ("0", "-100"):
            with self.subTest(amount=amount):
                self.raw.loc[self.raw["account_nm"] == "자본총계",
                             "thstrm_amount"] = amount
                metrics, details = self.calculate()
                self.assertTrue(pd.isna(metrics.iloc[0]["부채비율(%)"]))
                self.assertEqual(details["부채비율(%)"], "당기 자본총계 금액이 0 이하")

    def test_negative_inventory_is_distinct_from_missing_inventory(self):
        self.raw.loc[self.raw["account_nm"] == "재고자산",
                     "frmtrm_amount"] = "-100"
        metrics, details = self.calculate()
        self.assertTrue(pd.isna(metrics.iloc[0]["재고자산회전율(회)"]))
        self.assertIn("음수", details["재고자산회전율(회)"])
