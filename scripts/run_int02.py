import argparse
from pathlib import Path
from decimal import Decimal
import pandas as pd

from src.intangible_change import (
    analyze_intangible_change,
    EOK,
)

START = "<!-- INT02_START -->"
END = "<!-- INT02_END -->"


def format_number(value):
    if value is None:
        return "계산 불가"
    return f"{value:,.2f}"


def update_report(report_path, section):
    original = report_path.read_text(encoding="utf-8")

    if START in original:
        if END not in original:
            raise ValueError("보고서 INT-02 구역 표시가 잘못되었습니다.")

        before, remaining = original.split(START, 1)
        _, after = remaining.split(END, 1)

        updated = (
            before.rstrip() + "\n\n" +
            START + "\n" + section + "\n" + END +
            after
        )
    else:
        updated = (
            original.rstrip() + "\n\n" +
            START + "\n" + section + "\n" + END + "\n"
        )

    report_path.write_text(updated, encoding="utf-8")


def process_company(company, year, *, raw_path=None):
    if raw_path is None:
        files = list(Path("outputs").glob(f"{company}_{year}_*_raw.csv"))
        if len(files) != 1:
            raise ValueError(f"{company}: 원본 CSV {len(files)}개 발견")
        raw_path = files[0]

    output_dir = raw_path.parent
    report_dir = output_dir.parent / "reports"
    prefix = raw_path.stem.removesuffix("_raw")
    fs_div = prefix.rsplit("_", 1)[-1]

    raw = pd.read_csv(
        raw_path,
        dtype=str,
        encoding="utf-8-sig"
    ).fillna("")

    result = analyze_intangible_change(raw)

    # 기존 프로그램의 저장 비율과 교차 검증
    metrics_path = output_dir / (
        f"{prefix}_metrics.csv"
    )

    metrics = pd.read_csv(
        metrics_path,
        encoding="utf-8-sig"
    )

    if len(metrics) != 1:
        raise ValueError(f"{company}: 재무지표 행 수 확인 필요")

    saved = Decimal(
        str(metrics.iloc[0]["무형자산·영업권비중(%)"])
    )

    if abs(saved - result["ratio"]) >= Decimal("0.02"):
        raise ValueError(
            f"{company}: 기존 무형자산 비중과 불일치"
        )

    # 1. 원본 금액 기반 분석 결과 CSV
    screen = pd.DataFrame([{
        "기업": company,
        "사업연도": year,
        "재무제표기준": fs_div,
        "당기합계(원)": int(result["current"]),
        "전기합계(원)": int(result["previous"]),
        "증감액(원)": int(result["change"]),
        "증감률(%)": (
            str(result["change_rate"])
            if result["change_rate"] is not None
            else ""
        ),
        "총자산대비비중(%)": str(result["ratio"]),
        "INT-01": (
            "발생" if result["int01"] else "미발생"
        ),
        "INT-02": (
            "발생" if result["int02"] else "미발생"
        ),
    }])

    screen_path = output_dir / f"{prefix}_intangible_screen.csv"

    screen.to_csv(
        screen_path,
        index=False,
        encoding="utf-8-sig"
    )

    # 2. INT-02 발생 시 추가 PBC 생성
    pbc_columns = [
        "기업", "규칙", "요청자료",
        "검증목적", "검증절차"
    ]

    pbc_rows = []

    if result["int02"]:
        pbc_rows = [
            {
                "기업": company,
                "규칙": "INT-02",
                "요청자료": "무형자산·영업권 증감명세서",
                "검증목적": "당기 증가 원인 및 잔액 구성 파악",
                "검증절차": (
                    "기초잔액, 취득, 처분, 상각, "
                    "손상, 사업결합 등 변동내역 대사"
                ),
            },
            {
                "기업": company,
                "규칙": "INT-02",
                "요청자료": (
                    "주요 증가분의 계약서·취득증빙 및 "
                    "해당 시 개발비 자산화 근거"
                ),
                "검증목적": "주요 증가분의 인식 적정성 검토",
                "검증절차": (
                    "증가 유형별 증빙 확인 및 "
                    "관련 회계기준 검토"
                ),
            },
        ]

    pd.DataFrame(
        pbc_rows,
        columns=pbc_columns
    ).to_csv(
        output_dir / f"{prefix}_intangible_pbc.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # 3. 기존 Markdown 보고서에 추가
    report_path = report_dir / f"{prefix}_report.md"

    if not report_path.exists():
        raise FileNotFoundError(report_path)

    change_rate_text = format_number(
        result["change_rate"]
    )

    section = f"""## 무형자산·영업권 변동 분석 (INT-02)

| 검토 항목 | 결과 |
|---|---:|
| 당기 합계 | {format_number(result["current"] / EOK)}억 원 |
| 전기 합계 | {format_number(result["previous"] / EOK)}억 원 |
| 증감액 | {format_number(result["change"] / EOK)}억 원 |
| 증감률 | {change_rate_text}% |
| 총자산 대비 비중 | {format_number(result["ratio"])}% |
| INT-01 | {"발생" if result["int01"] else "미발생"} |
| INT-02 | {"발생" if result["int02"] else "미발생"} |

**INT-02 검토 의견:** {
    "무형자산·영업권 합계의 증가 구성 및 인식 근거 추가 확인"
    if result["int02"]
    else "설정된 INT-02 증가 조건 미충족"
}

**추천 PBC:** {
    "무형자산·영업권 증감명세서, 주요 증가분 증빙"
    if result["int02"]
    else "INT-02에 따른 추가 PBC 없음"
}

*INT-02의 100억 원 및 5% 기준은 학습용 임계값이며,
감사상 중요성이나 회계오류 여부를 의미하지 않습니다.*
"""

    update_report(report_path, section)

    print(
        f"{company}: INT-01="
        f"{'발생' if result['int01'] else '미발생'}, "
        f"INT-02="
        f"{'발생' if result['int02'] else '미발생'}"
    )

    return screen_path


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--company",
        nargs="+",
        required=True
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True
    )

    args = parser.parse_args()

    for company in args.company:
        process_company(company, args.year)

    print("\nINT-02 분석 및 보고서 반영 완료!")


if __name__ == "__main__":
    main()
