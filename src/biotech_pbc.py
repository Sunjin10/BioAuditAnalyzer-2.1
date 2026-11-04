
import pandas as pd

from src.pbc_engine import build_pbc_report, PBC_COLUMNS


# 사업모델별 추가 PBC
EXTRA_PBC = {
    "license": {
        "REV-01": [
            {
                "감사주장": "발생사실·기간귀속",
                "요청자료": "라이선스 계약서, 변경계약서, 수행의무 분석표",
                "검증목적": "라이선스 수익인식 조건 확인",
                "검증절차": "계약조건과 수행의무 이행증빙 대조",
                "적용조건": "라이선스 계약 수익이 존재하는 경우"
            },
            {
                "감사주장": "정확성·기간귀속",
                "요청자료": "마일스톤 달성증빙 및 대가 산정명세",
                "검증목적": "변동대가 금액과 인식시점 검토",
                "검증절차": "계약조건, 달성 사실 및 변동대가 제약 검토",
                "적용조건": "마일스톤 대가가 존재하는 경우"
            }
        ],
        "INT-01": [
            {
                "감사주장": "평가·배분",
                "요청자료": "프로젝트별 개발비 명세 및 자산화 판단자료",
                "검증목적": "개발비 자산화 요건 충족 여부 검토",
                "검증절차": "개발단계와 최초 자산화 시점의 근거 확인",
                "적용조건": "무형자산에 개발비가 포함된 경우"
            }
        ]
    },

    "manufacturing": {
        "INV-01": [
            {
                "감사주장": "평가·배분",
                "요청자료": "LOT별 유효기간, 재고 연령분석표, NRV 평가표",
                "검증목적": "장기체화 및 재고평가손실 검토",
                "검증절차": "유효기간과 판매실적, 예상 판매가격 검토",
                "적용조건": "유효기간 관리 대상 재고가 존재하는 경우"
            }
        ],
        "INV-02": [
            {
                "감사주장": "평가·배분",
                "요청자료": "제품별 판매실적, 생산계획, 재고수불부",
                "검증목적": "재고자산회전율 하락 원인 파악",
                "검증절차": "생산량, 판매량 및 기말재고 변동 분석",
                "적용조건": "제조·판매 재고가 존재하는 경우"
            }
        ],
        "INT-01": [
            {
                "감사주장": "평가·배분",
                "요청자료": "무형자산 유형별 명세 및 손상검토 자료",
                "검증목적": "무형자산의 구성과 평가 검토",
                "검증절차": "자산 유형별 손상검토 필요성과 근거 확인",
                "적용조건": "관련 무형자산이 존재하는 경우"
            }
        ]
    }
}


PBC_OUTPUT_COLUMNS = PBC_COLUMNS + [
    "검토우선순위", "추천유형", "적용조건"
]


def build_biotech_pbc_report(
    risk_df,
    business_model="unknown"
):
    """공통 PBC와 사업모델별 추가 PBC를 연결한다."""

    valid_models = {
        "unknown", "license", "manufacturing", "mixed"
    }

    if business_model not in valid_models:
        raise ValueError(
            f"지원하지 않는 사업모델: {business_model}"
        )

    # 1. 기존 2.0 공통 PBC 추천 함수 재사용
    base = build_pbc_report(risk_df)

    # 기존 검토우선순위 연결
    priority = risk_df[
        ["기업", "규칙", "검토우선순위"]
    ].drop_duplicates()

    base = base.merge(
        priority,
        on=["기업", "규칙"],
        how="left",
        validate="many_to_one"
    )

    base["추천유형"] = "공통"
    base["적용조건"] = "해당 계정 및 거래가 존재하는 경우"

    # 2. 선택한 사업모델에 따른 추가 자료 결정
    if business_model == "mixed":
        models = ["license", "manufacturing"]
    elif business_model == "unknown":
        models = []
    else:
        models = [business_model]

    extra_rows = []

    for _, risk in risk_df.iterrows():
        rule_id = risk["규칙"]

        for model in models:
            recommendations = EXTRA_PBC[
                model
            ].get(rule_id, [])

            for item in recommendations:
                extra_rows.append({
                    "기업": risk["기업"],
                    "규칙": rule_id,
                    "검토 신호": risk["검토 신호"],
                    "관련 기준": risk["관련 기준"],
                    "검토우선순위": risk["검토우선순위"],
                    "추천유형": f"{model} 특화",
                    **item
                })

    # 3. 공통 PBC + 사업모델 특화 PBC 결합
    extra_df = pd.DataFrame(extra_rows)

    result = pd.concat(
        [base, extra_df],
        ignore_index=True
    )

    return result.reindex(columns=PBC_OUTPUT_COLUMNS)
