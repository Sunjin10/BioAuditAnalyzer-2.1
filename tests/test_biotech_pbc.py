
import unittest
import pandas as pd

from src.biotech_pbc import build_biotech_pbc_report
from src.biotech_risk import build_biotech_risk_report


def sample_risk(rule="REV-01"):
    return pd.DataFrame([{
        "기업": "테스트기업",
        "사업모델": "license",
        "규칙": rule,
        "검토우선순위": "우선 검토",
        "검토 신호": "테스트 검토 신호",
        "근거": "테스트 수치",
        "관련 기준": "테스트 기준"
    }])


class TestBiotechPBC(unittest.TestCase):

    def test_license_revenue(self):
        # REV-01: 공통 2건 + 기술이전 특화 2건
        result = build_biotech_pbc_report(
            sample_risk("REV-01"),
            "license"
        )
        self.assertEqual(len(result), 4)

    def test_manufacturing_intangible(self):
        # INT-01: 공통 2건 + 제조형 특화 1건
        result = build_biotech_pbc_report(
            sample_risk("INT-01"),
            "manufacturing"
        )
        self.assertEqual(len(result), 3)

    def test_manufacturing_revenue(self):
        # 제조형 REV-01에는 공통 추천만 적용
        result = build_biotech_pbc_report(
            sample_risk("REV-01"),
            "manufacturing"
        )
        self.assertEqual(len(result), 2)

    def test_mixed_model(self):
        # 혼합형에 양쪽 추천 체계 적용
        result = build_biotech_pbc_report(
            sample_risk("REV-01"),
            "mixed"
        )
        self.assertEqual(len(result), 4)

    def test_unknown_model(self):
        # 미분류 기업은 공통 추천만 적용
        result = build_biotech_pbc_report(
            sample_risk("REV-01"),
            "unknown"
        )
        self.assertEqual(len(result), 2)

    def test_empty_risks(self):
        # 신호가 없어도 빈 보고서 구조 유지
        empty = sample_risk().iloc[0:0]

        result = build_biotech_pbc_report(
            empty, "license"
        )

        self.assertTrue(result.empty)
        self.assertIn("요청자료", result.columns)

    def test_invalid_model(self):
        with self.assertRaises(ValueError):
            build_biotech_pbc_report(
                sample_risk(),
                "invalid_model"
            )

    def test_integrated_flow(self):
        # 실제 API가 아닌 가상 재무지표로 통합 검증
        metrics = pd.DataFrame([{
            "기업": "가상바이오",
            "매출증가율(%)": 60.0,
            "재고증가율(%)": 65.0,
            "재고자산회전율(회)": 2.0,
            "전기재고자산회전율(회)": 2.0,
            "무형자산·영업권비중(%)": 16.0
        }])

        risk = build_biotech_risk_report(
            metrics, "license"
        )
        pbc = build_biotech_pbc_report(
            risk, "license"
        )

        self.assertEqual(
            set(risk["규칙"]),
            {"REV-01", "INT-01"}
        )
        self.assertEqual(len(pbc), 7)


if __name__ == "__main__":
    unittest.main()
