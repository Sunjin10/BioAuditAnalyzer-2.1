
import pandas as pd


RISK_COLUMNS = [
    "기업", "규칙", "검토 신호", "근거", "관련 기준"
]


def detect_signals(
    row,
    growth_gap_threshold=15,
    turnover_decline_threshold=5,
    revenue_growth_threshold=50,
    intangible_ratio_threshold=15
):
    signals = []
    company = row["기업"]

    revenue_growth = row["매출증가율(%)"]
    inventory_growth = row["재고증가율(%)"]
    turnover_2024 = row["2024년 회전율"]
    turnover_2025 = row["2025년 회전율"]
    intangible_ratio = row["무형자산비중(%)"]

    # INV-01: 재고 증가율이 매출 증가율보다 높음
    growth_gap = inventory_growth - revenue_growth

    if pd.notna(growth_gap) and growth_gap >= growth_gap_threshold:
        signals.append({
            "기업": company,
            "규칙": "INV-01",
            "검토 신호": "재고 증가율이 매출 증가율을 크게 상회",
            "근거": f"증가율 격차 {growth_gap:.2f}%p",
            "관련 기준": "K-IFRS 제1002호"
        })

    # INV-02: 재고자산회전율 하락
    if (
        pd.notna(turnover_2024)
        and pd.notna(turnover_2025)
        and turnover_2024 > 0
    ):
        decline = (
            (turnover_2024 - turnover_2025)
            / turnover_2024 * 100
        )

        if decline >= turnover_decline_threshold:
            signals.append({
                "기업": company,
                "규칙": "INV-02",
                "검토 신호": "재고자산회전율 하락",
                "근거": f"전년 대비 {decline:.2f}% 하락",
                "관련 기준": "K-IFRS 제1002호"
            })

    # REV-01: 매출 급증
    if (
        pd.notna(revenue_growth)
        and revenue_growth >= revenue_growth_threshold
    ):
        signals.append({
            "기업": company,
            "규칙": "REV-01",
            "검토 신호": "매출액의 큰 폭 증가",
            "근거": f"매출 증가율 {revenue_growth:.2f}%",
            "관련 기준": "K-IFRS 제1115호"
        })

    # INT-01: 무형자산 비중
    if (
        pd.notna(intangible_ratio)
        and intangible_ratio >= intangible_ratio_threshold
    ):
        signals.append({
            "기업": company,
            "규칙": "INT-01",
            "검토 신호": "무형자산 비중이 높음",
            "근거": f"총자산 대비 {intangible_ratio:.2f}%",
            "관련 기준": "K-IFRS 제1038호 / 제1036호"
        })

    return signals


def build_risk_report(metrics_df):
    # 필요한 열이 모두 있는지 확인
    required = [
        "기업", "매출증가율(%)", "재고증가율(%)",
        "2024년 회전율", "2025년 회전율",
        "무형자산비중(%)"
    ]

    missing = set(required) - set(metrics_df.columns)

    if missing:
        raise ValueError(f"필수 열 누락: {missing}")

    if metrics_df["기업"].duplicated().any():
        raise ValueError("기업 데이터가 중복되었습니다.")

    results = []

    for _, row in metrics_df.iterrows():
        results.extend(detect_signals(row))

    return pd.DataFrame(results, columns=RISK_COLUMNS)
