
import pandas as pd


# 사업모델별 우선 검토 규칙
MODEL_PRIORITY = {
    "unknown": set(),
    "license": {"REV-01", "INT-01"},
    "manufacturing": {"INV-01", "INV-02"},
    "mixed": {"INV-01", "INV-02", "REV-01", "INT-01"}
}


def build_biotech_risk_report(
    metrics_df,
    business_model="unknown"
):
    """제약·바이오 재무지표의 추가 검토 신호를 생성한다."""

    if business_model not in MODEL_PRIORITY:
        raise ValueError("지원하지 않는 사업모델입니다.")

    if len(metrics_df) != 1:
        raise ValueError("한 기업의 재무지표만 입력하세요.")

    row = metrics_df.iloc[0]
    company = row["기업"]
    signals = []

    def add_signal(rule, description, evidence, standard):
        priority = (
            "우선 검토"
            if rule in MODEL_PRIORITY[business_model]
            else "보조 검토"
        )

        signals.append({
            "기업": company,
            "사업모델": business_model,
            "규칙": rule,
            "검토우선순위": priority,
            "검토 신호": description,
            "근거": evidence,
            "관련 기준": standard
        })

    # REV-01: 매출 증가율 50% 이상
    revenue_growth = row.get("매출증가율(%)")

    if pd.notna(revenue_growth) and revenue_growth >= 50:
        add_signal(
            "REV-01",
            "매출액의 큰 폭 증가",
            f"매출 증가율 {revenue_growth:.2f}%",
            "K-IFRS 제1115호"
        )

    # INT-01: 무형자산 비중 15% 이상
    intangible_ratio = row.get("무형자산·영업권비중(%)")

    if pd.notna(intangible_ratio) and intangible_ratio >= 15:
        add_signal(
            "INT-01",
            "총자산 대비 무형자산 비중이 높음",
            f"무형자산 비중 {intangible_ratio:.2f}%",
            "K-IFRS 제1038호 / 제1036호"
        )

    # INV-01: 재고 증가율이 매출 증가율을 15%p 이상 상회
    inventory_growth = row.get("재고증가율(%)")

    if pd.notna(inventory_growth) and pd.notna(revenue_growth):
        gap = inventory_growth - revenue_growth

        if gap >= 15:
            add_signal(
                "INV-01",
                "재고 증가율이 매출 증가율을 크게 상회",
                f"증가율 격차 {gap:.2f}%p",
                "K-IFRS 제1002호"
            )

    # INV-02: 재고자산회전율 5% 이상 하락
    current_turnover = row.get("재고자산회전율(회)")
    previous_turnover = row.get("전기재고자산회전율(회)")

    if (
        pd.notna(current_turnover)
        and pd.notna(previous_turnover)
        and previous_turnover > 0
    ):
        decline = (
            (previous_turnover - current_turnover)
            / previous_turnover * 100
        )

        if decline >= 5:
            add_signal(
                "INV-02",
                "재고자산회전율 하락",
                f"전년 대비 {decline:.2f}% 하락",
                "K-IFRS 제1002호"
            )

    columns = [
        "기업", "사업모델", "규칙",
        "검토우선순위", "검토 신호", "근거", "관련 기준"
    ]

    report = pd.DataFrame(signals, columns=columns)

    if not report.empty:
        report["_order"] = report["검토우선순위"].map({
            "우선 검토": 0,
            "보조 검토": 1
        })
        report = (
            report.sort_values("_order")
            .drop(columns="_order")
            .reset_index(drop=True)
        )

    return report
