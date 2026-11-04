from pathlib import Path
from decimal import Decimal

import pandas as pd

from src.intangible_change import EOK


RISK_COLUMNS = [
    "기업", "사업모델", "규칙", "검토우선순위",
    "검토 신호", "근거", "관련 기준"
]

PBC_COLUMNS = [
    "기업", "규칙", "검토 신호", "관련 기준",
    "감사주장", "요청자료", "검증목적",
    "검증절차", "검토우선순위",
    "추천유형", "적용조건"
]


def read_checked_csv(path, required_columns):
    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig"
    )

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{path.name}: 필요한 열 누락 {missing}"
        )

    return df


def merge_int02(
    company,
    year,
    business_model="unknown",
    output_dir="outputs"
):
    output_dir = Path(output_dir)

    # 1. INT-02 분석 결과 파일 찾기
    screen_files = list(
        output_dir.glob(
            f"{company}_{year}_*_intangible_screen.csv"
        )
    )

    if len(screen_files) != 1:
        raise ValueError(
            f"{company}: INT-02 분석 파일 "
            f"{len(screen_files)}개 발견"
        )

    screen_path = screen_files[0]

    prefix = screen_path.name[
        :-len("_intangible_screen.csv")
    ]

    risk_path = output_dir / f"{prefix}_risk.csv"
    pbc_path = output_dir / f"{prefix}_pbc.csv"

    extra_pbc_path = (
        output_dir / f"{prefix}_intangible_pbc.csv"
    )

    # 2. 기존 파일 읽기
    screen = read_checked_csv(
        screen_path,
        ["기업", "사업연도", "INT-02",
         "증감액(원)", "증감률(%)"]
    )

    risk = read_checked_csv(
        risk_path, RISK_COLUMNS
    )

    pbc = read_checked_csv(
        pbc_path, PBC_COLUMNS
    )

    if len(screen) != 1:
        raise ValueError("INT-02 분석 결과는 1행이어야 합니다.")

    row = screen.iloc[0]

    if (
        row["기업"] != company
        or row["사업연도"] != str(year)
    ):
        raise ValueError("기업명 또는 사업연도가 일치하지 않습니다.")

    if row["INT-02"] not in ("발생", "미발생"):
        raise ValueError("INT-02 판정값을 확인해야 합니다.")

    # 3. 기존 INT-02 행 제거
    # 다른 규칙의 행은 모두 유지
    risk_updated = risk.loc[
        risk["규칙"] != "INT-02"
    ].copy()

    pbc_updated = pbc.loc[
        pbc["규칙"] != "INT-02"
    ].copy()

    # 4. INT-02가 발생한 경우에만 추가
    if row["INT-02"] == "발생":

        change = Decimal(row["증감액(원)"])
        rate = Decimal(row["증감률(%)"])

        # 분석 결과의 임계값 검증
        if (
            change < Decimal("10000000000")
            or rate < Decimal("5")
        ):
            raise ValueError(
                "INT-02 판정과 계산값이 일치하지 않습니다."
            )

        change_eok = change / EOK

        # 위험 탐지 결과 1행
        new_risk = {
            "기업": company,
            "사업모델": business_model,
            "규칙": "INT-02",
            "검토우선순위": "보조 검토",
            "검토 신호": "무형자산·영업권 합계 증가",
            "근거": (
                f"증가액 {change_eok:,.2f}억 원, "
                f"증가율 {rate:.2f}% "
                "(학습용 기준: 100억 원 및 5%)"
            ),
            "관련 기준": (
                "K-IFRS 제1038호·제1036호"
            )
        }

        risk_updated = pd.concat(
            [
                risk_updated,
                pd.DataFrame([new_risk])
            ],
            ignore_index=True
        )

        # 5. 기존 INT-02 전용 PBC 불러오기
        extra_pbc = read_checked_csv(
            extra_pbc_path,
            [
                "기업", "규칙", "요청자료",
                "검증목적", "검증절차"
            ]
        )

        if extra_pbc.empty:
            raise ValueError(
                f"{company}: INT-02 추가 PBC가 없습니다."
            )

        if not (
            extra_pbc["기업"].eq(company).all()
            and extra_pbc["규칙"].eq("INT-02").all()
        ):
            raise ValueError(
                "INT-02 추가 PBC의 기업명 또는 규칙이 다릅니다."
            )

        new_pbc_rows = []

        for _, item in extra_pbc.iterrows():
            new_pbc_rows.append({
                "기업": company,
                "규칙": "INT-02",
                "검토 신호": "무형자산·영업권 합계 증가",
                "관련 기준": (
                    "K-IFRS 제1038호·제1036호"
                ),
                "감사주장": "평가",
                "요청자료": item["요청자료"],
                "검증목적": item["검증목적"],
                "검증절차": item["검증절차"],
                "검토우선순위": "보조 검토",
                "추천유형": "추가 분석",
                "적용조건": (
                    "INT-02 발생 및 관련 거래·잔액 존재 시"
                )
            })

        pbc_updated = pd.concat(
            [
                pbc_updated,
                pd.DataFrame(new_pbc_rows)
            ],
            ignore_index=True
        )

    # 6. 원래 열 순서 유지
    risk_updated = risk_updated[risk.columns]
    pbc_updated = pbc_updated[pbc.columns]

    # 7. 기존 CSV 갱신
    risk_updated.to_csv(
        risk_path,
        index=False,
        encoding="utf-8-sig"
    )

    pbc_updated.to_csv(
        pbc_path,
        index=False,
        encoding="utf-8-sig"
    )

    print(
        f"{company}: 통합 완료 "
        f"(RISK {len(risk_updated)}행, "
        f"PBC {len(pbc_updated)}행)"
    )

    return risk_updated, pbc_updated
