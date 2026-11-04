from decimal import Decimal, InvalidOperation

EOK = Decimal("100000000")

INTANGIBLE_ID = "ifrs-full_IntangibleAssetsAndGoodwill"
ASSETS_ID = "ifrs-full_Assets"


def get_bs_amount(raw, account_id, period):
    """재무상태표의 정확한 표준계정 ID에서 금액 추출"""

    rows = raw[
        (raw["sj_div"] == "BS") &
        (raw["account_id"] == account_id)
    ]

    if len(rows) != 1:
        raise ValueError(
            f"{account_id}: 계정 검색 결과 {len(rows)}건"
        )

    text = str(rows.iloc[0][period]).strip().replace(",", "")

    if text in ("", "-", "nan", "None"):
        raise ValueError(
            f"{account_id}: {period} 금액이 없습니다."
        )

    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(
            f"{account_id}: 숫자 형식 오류 ({text})"
        ) from exc

    if not value.is_finite():
        raise ValueError(
            f"{account_id}: 유효하지 않은 금액"
        )

    return value


def analyze_intangible_change(raw):
    """INT-01과 INT-02를 원본 금액으로 계산"""

    current = get_bs_amount(
        raw, INTANGIBLE_ID, "thstrm_amount"
    )

    previous = get_bs_amount(
        raw, INTANGIBLE_ID, "frmtrm_amount"
    )

    assets = get_bs_amount(
        raw, ASSETS_ID, "thstrm_amount"
    )

    if assets <= 0 or current < 0 or previous < 0:
        raise ValueError("자산 금액을 확인해야 합니다.")

    ratio = current / assets * 100
    change = current - previous

    # 전기 잔액이 0이면 증가율 계산 불가
    change_rate = (
        change / previous * 100
        if previous > 0
        else None
    )

    # 기존 학습용 규칙
    int01 = ratio >= Decimal("15")

    # 신규 학습용 규칙: 100억 원 이상 & 5% 이상
    int02 = (
        change >= Decimal("10000000000")
        and change_rate is not None
        and change_rate >= Decimal("5")
    )

    return {
        "current": current,
        "previous": previous,
        "assets": assets,
        "ratio": ratio,
        "change": change,
        "change_rate": change_rate,
        "int01": int01,
        "int02": int02,
    }
