
import unittest
import tempfile
from pathlib import Path
import pandas as pd

from src.report_writer import save_company_report


class TestReportWriter(unittest.TestCase):

    def setUp(self):
        # 실제 공시가 아닌 테스트용 가상 데이터
        self.metrics = pd.DataFrame([{
            "기업": "가상바이오",
            "사업연도": 2025,
            "재무제표기준": "CFS",
            "매출증가율(%)": 60.0,
            "영업이익률(%)": 12.53
        }])

        self.focus = pd.DataFrame([{
            "검토항목": "수익인식",
            "재무지표": "매출증가율(%)",
            "지표값": 60.0,
            "계산상태": "계산됨",
            "검증목적": "매출 증가 원인 확인"
        }])

        self.risk = pd.DataFrame([{
            "규칙": "REV-01",
            "검토우선순위": "우선 검토",
            "검토 신호": "매출액 급증",
            "근거": "매출 증가율 60%",
            "관련 기준": "K-IFRS 제1115호"
        }])

        self.pbc = pd.DataFrame([{
            "규칙": "REV-01",
            "추천유형": "기술이전 특화",
            "요청자료": "라이선스 계약서",
            "적용조건": "라이선스 수익이 존재하는 경우",
            "검증목적": "수익인식 조건 확인",
            "검증절차": "계약조건과 이행증빙 대조"
        }])

    def save_test_report(self, path, **kwargs):
        options = {
            "metrics_df": self.metrics,
            "focus_df": self.focus,
            "risk_df": self.risk,
            "pbc_df": self.pbc,
            "business_model": "license",
            "output_path": path
        }
        options.update(kwargs)
        return save_company_report(**options)

    def test_01_report_created(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report.md"
            self.save_test_report(path)

            self.assertTrue(path.exists())

            content = path.read_text(encoding="utf-8")
            self.assertIn("가상바이오", content)
            self.assertIn("2025년", content)

    def test_02_metrics_and_pbc(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report.md"
            self.save_test_report(path)

            content = path.read_text(encoding="utf-8")

            self.assertIn("12.53", content)
            self.assertIn("REV-01", content)
            self.assertIn("K-IFRS 제1115호", content)
            self.assertIn("라이선스 계약서", content)
            self.assertIn("탐지된 신호 수: 1건", content)

    def test_03_source_reference(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report.md"

            self.save_test_report(
                path,
                receipt_no="12345678901234"
            )

            content = path.read_text(encoding="utf-8")

            self.assertIn(
                "DART 접수번호: 12345678901234",
                content
            )

    def test_04_empty_signals(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report.md"

            self.save_test_report(
                path,
                risk_df=pd.DataFrame(),
                pbc_df=pd.DataFrame()
            )

            content = path.read_text(encoding="utf-8")

            self.assertIn("탐지된 신호 수: 0건", content)
            self.assertIn("해당 항목 없음", content)

    def test_05_missing_required_column(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report.md"

            invalid_focus = self.focus.drop(
                columns=["검증목적"]
            )

            with self.assertRaises(ValueError):
                self.save_test_report(
                    path,
                    focus_df=invalid_focus
                )


if __name__ == "__main__":
    unittest.main()
