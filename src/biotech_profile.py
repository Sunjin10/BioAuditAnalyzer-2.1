
import pandas as pd


# 사업모델 구분
MODEL_NAMES = {
    "unknown": "미분류",
    "license": "기술이전·신약개발형",
    "manufacturing": "의약품 제조·판매형",
    "mixed": "혼합형"
}


# 모든 기업에 공통으로 적용할 분석 항목
COMMON_FOCUS = [
    {
        "검토항목": "매출 구성 및 수익인식",
        "지표": "매출증가율(%)",
        "추천 PBC": "매출 유형별 명세, 주요 계약서",
        "검증목적": "매출 변동 원인과 수익인식 조건 확인"
    },
    {
        "검토항목": "수익성 분석",
        "지표": "영업이익률(%)",
        "추천 PBC": "매출 유형별 손익 및 비용 명세",
        "검증목적": "수익성 변동 원인 파악"
    },
    {
        "검토항목": "유동성 분석",
        "지표": "유동비율(%)",
        "추천 PBC": "현금흐름표, 차입금 및 상환계획",
        "검증목적": "단기 지급능력 관련 검토"
    }
]


# 기술이전·신약개발형 추가 분석
LICENSE_FOCUS = [
    {
        "검토항목": "기술이전 및 마일스톤 수익",
        "지표": "매출증가율(%)",
        "추천 PBC": "라이선스 계약서, 마일스톤 달성증빙",
        "검증목적": "계약조건과 수익인식 시점 검토"
    },
    {
        "검토항목": "연구개발 및 무형자산",
        "지표": "무형자산비중(%)",
        "추천 PBC": "무형자산 주석, 프로젝트별 개발비 명세",
        "검증목적": "자산 구성 및 자산화·손상 검토 대상 파악"
    },
    {
        "검토항목": "연구개발 자금조달",
        "지표": "유동비율(%)",
        "추천 PBC": "영업현금흐름, 연구개발 예산, 자금계획",
        "검증목적": "연구개발 자금조달 여력 추가 검토"
    }
]


# 의약품 제조·판매형 추가 분석
MANUFACTURING_FOCUS = [
    {
        "검토항목": "재고 누적 및 판매 가능성",
        "지표": "재고증가율(%)",
        "추천 PBC": "재고 연령분석표, LOT별 유효기간",
        "검증목적": "장기체화 및 판매 가능성 검토"
    },
    {
        "검토항목": "재고자산회전율",
        "지표": "재고자산회전율(회)",
        "추천 PBC": "재고수불부, 품목별 판매실적",
        "검증목적": "재고 회전 및 누적 원인 파악"
    },
    {
        "검토항목": "매출원가 구조",
        "지표": "매출원가율(%)",
        "추천 PBC": "제품별 원가명세, 생산실적",
        "검증목적": "원가 변동 및 배부 방식 검토"
    }
]


def build_focus_report(metrics_df, business_model="unknown"):
    """사업모델에 따라 중점 검토항목을 생성한다."""

    if business_model not in MODEL_NAMES:
        raise ValueError(
            f"지원하지 않는 사업모델: {business_model}"
        )

    if len(metrics_df) != 1:
        raise ValueError(
            "한 번에 한 기업의 재무지표만 입력하세요."
        )

    row = metrics_df.iloc[0]

    # 공통 분석항목은 항상 포함
    focus_items = COMMON_FOCUS.copy()

    # 사업모델별 검토항목 추가
    if business_model in ("license", "mixed"):
        focus_items.extend(LICENSE_FOCUS)

    if business_model in ("manufacturing", "mixed"):
        focus_items.extend(MANUFACTURING_FOCUS)

    results = []

    for item in focus_items:
        metric_name = item["지표"]
        value = row.get(metric_name)

        if pd.isna(value):
            result_value = None
            status = "계산 불가"
        else:
            result_value = round(float(value), 2)
            status = "계산됨"

        results.append({
            "기업": row["기업"],
            "분석유형": MODEL_NAMES[business_model],
            "검토항목": item["검토항목"],
            "재무지표": metric_name,
            "지표값": result_value,
            "계산상태": status,
            "추천 PBC": item["추천 PBC"],
            "검증목적": item["검증목적"]
        })

    return pd.DataFrame(results)
