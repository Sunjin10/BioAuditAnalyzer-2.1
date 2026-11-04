
import pandas as pd


# 표준계정 ID와 대체 계정명
# 회사마다 표시하는 계정명이 다를 수 있으므로 ID를 우선 사용
ACCOUNT_MAP = {
    "매출액": (
        ["CIS", "IS"],
        ["ifrs-full_Revenue", "ifrs_Revenue"],
        ["수익(매출액)", "매출액", "영업수익"]
    ),
    "영업이익": (
        ["CIS", "IS"],
        ["dart_OperatingIncomeLoss"],
        ["영업이익(손실)", "영업이익"]
    ),
    "매출원가": (
        ["CIS", "IS"],
        ["ifrs-full_CostOfSales", "ifrs_CostOfSales"],
        ["매출원가"]
    ),
    "자산총계": (
        ["BS"],
        ["ifrs-full_Assets", "ifrs_Assets"],
        ["자산총계"]
    ),
    "부채총계": (
        ["BS"],
        ["ifrs-full_Liabilities", "ifrs_Liabilities"],
        ["부채총계"]
    ),
    "자본총계": (
        ["BS"],
        ["ifrs-full_Equity", "ifrs_Equity"],
        ["자본총계"]
    ),
    "유동자산": (
        ["BS"],
        ["ifrs-full_CurrentAssets", "ifrs_CurrentAssets"],
        ["유동자산"]
    ),
    "유동부채": (
        ["BS"],
        ["ifrs-full_CurrentLiabilities", "ifrs_CurrentLiabilities"],
        ["유동부채"]
    ),
    "재고자산": (
        ["BS"],
        ["ifrs-full_Inventories", "ifrs_Inventories"],
        ["재고자산"]
    ),
    "무형자산": (
        ["BS"],
        [
            "ifrs-full_IntangibleAssetsOtherThanGoodwill",
            "ifrs_IntangibleAssetsOtherThanGoodwill"
        ],
        ["무형자산"]
    )
}


def parse_amount(value):
    """금액 문자열을 정수로 변환한다."""
    if pd.isna(value):
        return None

    text = str(value).strip().replace(",", "")

    if text in ("", "-", "nan"):
        return None

    # 괄호로 표시한 음수 처리
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]

    return int(text)


def get_amount(fs, account, period):
    """표준계정 ID를 우선 검색하고 금액을 가져온다."""
    statements, ids, names = ACCOUNT_MAP[account]

    for statement in statements:
        base = fs[fs["sj_div"] == statement]

        # 표준계정 ID 우선
        rows = base[base["account_id"].isin(ids)]

        # 없으면 정확한 계정명으로 재검색
        if rows.empty:
            rows = base[base["account_nm"].isin(names)]

        if len(rows) > 1:
            raise ValueError(
                f"{account}: 계정이 중복되었습니다. 원문 확인 필요"
            )

        if len(rows) == 1:
            return parse_amount(rows.iloc[0][period])

    return None


def safe_ratio(numerator, denominator, multiplier=1):
    """분모가 유효할 때만 비율을 계산한다."""
    if numerator is None or denominator is None:
        return None

    if denominator <= 0:
        return None

    return numerator / denominator * multiplier


def growth_rate(current, previous):
    """전년 대비 증가율 계산."""
    if current is None or previous is None:
        return None

    if previous <= 0:
        return None

    return (current / previous - 1) * 100


def to_eok(amount):
    """원 단위 금액을 억 원으로 변환."""
    return None if amount is None else amount / 100_000_000


def average_inventory(first, last):
    if first is None or last is None:
        return None

    if first < 0 or last < 0:
        return None

    return (first + last) / 2


def calculate_metrics(fs, company, year, fs_div):
    """기업별 재무지표를 자동 계산한다."""

    # 금액 단위 확인
    if "currency" in fs.columns:
        currencies = set(
            fs["currency"].dropna().astype(str).str.strip()
        ) - {""}

        if not currencies.issubset({"KRW", "원"}):
            raise ValueError(
                f"금액의 표시통화·단위를 확인하세요: {currencies}"
            )

    # 당기 / 전기 / 전전기
    def current(account):
        return get_amount(fs, account, "thstrm_amount")

    def previous(account):
        return get_amount(fs, account, "frmtrm_amount")

    def before_previous(account):
        return get_amount(fs, account, "bfefrmtrm_amount")

    revenue = current("매출액")
    prev_revenue = previous("매출액")

    operating_profit = current("영업이익")
    cogs = current("매출원가")
    prev_cogs = previous("매출원가")

    assets = current("자산총계")
    liabilities = current("부채총계")
    equity = current("자본총계")

    current_assets = current("유동자산")
    current_liabilities = current("유동부채")

    inventory = current("재고자산")
    prev_inventory = previous("재고자산")
    old_inventory = before_previous("재고자산")

    intangibles = current("무형자산")

    avg_inventory = average_inventory(
        prev_inventory, inventory
    )
    prev_avg_inventory = average_inventory(
        old_inventory, prev_inventory
    )

    metrics = {
        "기업": company,
        "사업연도": year,
        "재무제표기준": fs_div,
        "매출액(억 원)": to_eok(revenue),
        "영업이익(억 원)": to_eok(operating_profit),
        "매출증가율(%)": growth_rate(
            revenue, prev_revenue
        ),
        "영업이익률(%)": safe_ratio(
            operating_profit, revenue, 100
        ),
        "매출원가율(%)": safe_ratio(
            cogs, revenue, 100
        ),
        "부채비율(%)": safe_ratio(
            liabilities, equity, 100
        ),
        "유동비율(%)": safe_ratio(
            current_assets, current_liabilities, 100
        ),
        "재고증가율(%)": growth_rate(
            inventory, prev_inventory
        ),
        "재고자산회전율(회)": safe_ratio(
            cogs, avg_inventory
        ),
        "전기재고자산회전율(회)": safe_ratio(
            prev_cogs, prev_avg_inventory
        ),
        "무형자산비중(%)": safe_ratio(
            intangibles, assets, 100
        )
    }

    return pd.DataFrame([metrics])
