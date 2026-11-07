import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts import run_company, run_full_analysis
from src.financial_metrics import calculate_metrics


class FullAnalysisTests(unittest.TestCase):
    def test_uses_current_run_files_with_official_name_and_scope(self):
        company = {"corp_name": "테스트 제약", "corp_code": "00000001",
                   "stock_code": "000001"}
        registry = pd.DataFrame([company])
        raw = pd.DataFrame([
            {"sj_div": "BS", "account_id": "ifrs-full_Assets",
             "account_nm": "자산총계", "thstrm_amount": "100000000000"},
            {"sj_div": "BS", "account_id": "ifrs-full_IntangibleAssetsAndGoodwill",
             "account_nm": "무형자산 및 영업권",
             "thstrm_amount": "30000000000", "frmtrm_amount": "15000000000"},
        ])

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outputs = root / "outputs"
            outputs.mkdir()
            for suffix in ("raw", "intangible_screen", "risk", "pbc"):
                (outputs / f"테스트_제약_2025_OFS_{suffix}.csv").write_text(
                    "stale", encoding="utf-8"
                )

            args = ["run_full_analysis", "--company", "주식회사 테스트제약",
                    "--year", "2025", "--model", "mixed"]
            with (
                patch("sys.argv", args),
                patch.object(run_company, "PROJECT_ROOT", root),
                patch.object(run_company, "OUTPUT_DIR", outputs),
                patch.object(run_company, "getpass", return_value="test-placeholder"),
                patch.object(run_company, "get_corp_list", return_value=registry),
                patch.object(run_company, "get_financial_statements",
                             return_value=(raw, "CFS")),
                redirect_stdout(io.StringIO()),
            ):
                for _ in range(2):
                    run_full_analysis.main()

            prefix = "테스트_제약_2025_CFS"
            risk = pd.read_csv(outputs / f"{prefix}_risk.csv")
            pbc = pd.read_csv(outputs / f"{prefix}_pbc.csv")
            report = (root / "reports" / f"{prefix}_report.md").read_text(
                encoding="utf-8"
            )
            self.assertEqual(risk["규칙"].eq("INT-02").sum(), 1)
            self.assertEqual(pbc["규칙"].eq("INT-02").sum(), 2)
            self.assertEqual(report.count("<!-- INT02_START -->"), 1)
            self.assertIn("계산 근거·불가 이유", report)
            self.assertIn("당기 매출액 · 전기 매출액 금액 없음", report)
            self.assertIn("30,000,000,000원 ÷ 100,000,000,000원 × 100",
                          report)
            for stale in outputs.glob("*_OFS_*.csv"):
                self.assertEqual(stale.read_text(encoding="utf-8"), "stale")

    def test_missing_older_comparative_does_not_block_current_turnover(self):
        raw = pd.DataFrame([
            {"sj_div": "BS", "account_id": "ifrs-full_Inventories",
             "account_nm": "재고자산", "thstrm_amount": "30",
             "frmtrm_amount": "10"},
            {"sj_div": "IS", "account_id": "ifrs-full_CostOfSales",
             "account_nm": "매출원가", "thstrm_amount": "40",
             "frmtrm_amount": "30"},
        ])
        metrics = calculate_metrics(raw, "테스트 제약", 2025, "CFS").iloc[0]
        self.assertEqual(metrics["재고자산회전율(회)"], 2)
        self.assertTrue(pd.isna(metrics["전기재고자산회전율(회)"]))
