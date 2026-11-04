
from pathlib import Path
from numbers import Real
import pandas as pd


def format_value(value):
    """보고서에 표시할 값의 형식을 정한다."""
    if pd.isna(value):
        return "계산 불가"

    if isinstance(value, Real) and not isinstance(value, bool):
        return f"{value:,.2f}"

    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown_table(df, columns):
    """DataFrame을 Markdown 표로 변환한다."""
    if df.empty:
        return "해당 항목 없음\n"

    missing = set(columns) - set(df.columns)

    if missing:
        raise ValueError(f"보고서 필수 열 누락: {missing}")

    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(
        ["---"] * len(columns)
    ) + " |"

    rows = []

    for _, row in df.iterrows():
        values = [
            format_value(row[col]) for col in columns
        ]
        rows.append("| " + " | ".join(values) + " |")

    return "\n".join([header, separator] + rows) + "\n"


def save_company_report(
    metrics_df,
    focus_df,
    risk_df,
    pbc_df,
    business_model,
    output_path,
    receipt_no=None
):
    """기업별 재무·감사 분석 결과를 Markdown으로 저장한다."""

    if len(metrics_df) != 1:
        raise ValueError("한 기업의 분석 결과만 입력하세요.")

    row = metrics_df.iloc[0]

    company = str(row["기업"])
    year = int(row["사업연도"])
    fs_div = str(row["재무제표기준"])

    fs_name = {
        "CFS": "연결재무제표",
        "OFS": "별도재무제표"
    }.get(fs_div, fs_div)

    # 기본 재무지표를 세로형 표로 변환
    metadata = {"기업", "사업연도", "재무제표기준"}

    metric_rows = [
        {"지표": col, "값": row[col]}
        for col in metrics_df.columns
        if col not in metadata
    ]

    metric_table = markdown_table(
        pd.DataFrame(metric_rows),
        ["지표", "값"]
    )

    focus_table = markdown_table(
        focus_df,
        ["검토항목", "재무지표", "지표값", "계산상태", "검증목적"]
    )

    risk_table = markdown_table(
        risk_df,
        ["규칙", "검토우선순위", "검토 신호", "근거", "관련 기준"]
    )

    pbc_table = markdown_table(
        pbc_df,
        ["규칙", "추천유형", "요청자료", "적용조건", "검증목적", "검증절차"]
    )

    # 원본 사업보고서 추적 정보
    source_detail = ""

    if receipt_no:
        source_detail = (
            f"- DART 접수번호: {receipt_no}\n"
            f"- 공시 원문: "
            f"https://dart.fss.or.kr/dsaf001/main.do"
            f"?rcpNo={receipt_no}\n"
        )

    report = f"""# {company} | {year}년 재무·감사 분석 보고서

## 1. 분석 개요

- 기업: {company}
- 사업연도: {year}
- 재무제표 기준: {fs_name}
- 사업모델 설정: {business_model}
- 데이터 출처: 금융감독원 OpenDART, 사업보고서
{source_detail}
본 보고서는 공개 재무정보를 이용한 학습용 분석이다.

## 2. 주요 재무지표

{metric_table}
## 3. 사업모델별 중점 검토항목

{focus_table}
## 4. 규칙 기반 추가 검토 신호

{risk_table}
탐지된 신호 수: {len(risk_df)}건

검토 신호가 없더라도 회계위험이 없다는 뜻은 아니다.

## 5. 추천 PBC 및 검증절차

{pbc_table}
추천 자료 항목 수: {len(pbc_df)}건

추천 PBC는 실제로 수령하거나 검증한 감사증거가 아니다.

## 6. 분석의 한계

1. 본 보고서는 실제 감사의견이나 회계오류 판정이 아니다.
2. 탐지 기준은 학습용 임계값이며, 공식 감사위험 판정기준이 아니다.
3. 사업모델은 사용자가 지정하며 자동으로 검증하지 않는다.
4. 공개 재무제표만으로 계약조건, LOT별 유효기간,
   개발비 자산화의 적정성 등을 확정할 수 없다.
5. 실제 감사에서는 자료의 완전성·정확성 및
   충분하고 적합한 감사증거를 별도로 검토해야 한다.
"""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")

    return path
