
from pathlib import Path
import pandas as pd

from src.risk_engine import build_risk_report
from src.pbc_engine import build_pbc_report


# 프로젝트 및 출력 폴더
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"


def load_csv(filename):
    """저장된 CSV 파일을 불러온다."""
    path = OUTPUT_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    return pd.read_csv(path, encoding="utf-8-sig")


def prepare_metrics():
    """기업별 위험 탐지 입력 데이터를 구성한다."""

    kpis = load_csv("financial_kpis_2025.csv")
    growth = load_csv("financial_growth_2025.csv")
    inventory = load_csv("inventory_analysis.csv")

    # 재고자산 증가율
    inventory_growth = growth.loc[
        growth["계정"] == "재고자산",
        ["기업", "증가율(%)"]
    ].rename(columns={
        "증가율(%)": "재고증가율(%)"
    })

    # 자산총계 대비 무형자산 비중
    assets = growth.loc[
        growth["계정"].isin(["자산총계", "무형자산"])
    ].pivot(
        index="기업",
        columns="계정",
        values="2025년(억 원)"
    ).reset_index()

    if (assets["자산총계"] <= 0).any():
        raise ValueError("자산총계가 0 이하입니다.")

    assets["무형자산비중(%)"] = (
        assets["무형자산"] / assets["자산총계"] * 100
    )

    # 세 데이터 결합
    metrics = (
        kpis[["기업", "매출증가율(%)"]]
        .merge(
            inventory_growth,
            on="기업",
            validate="one_to_one"
        )
        .merge(
            inventory[
                ["기업", "2024년 회전율", "2025년 회전율"]
            ],
            on="기업",
            validate="one_to_one"
        )
        .merge(
            assets[["기업", "무형자산비중(%)"]],
            on="기업",
            validate="one_to_one"
        )
    )

    if metrics.empty:
        raise ValueError("분석할 기업 데이터가 없습니다.")

    if metrics.isna().any().any():
        raise ValueError("위험 탐지 입력 데이터에 결측값이 있습니다.")

    return metrics


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 분석 입력 데이터 준비
    metrics = prepare_metrics()

    # 2. 감사 검토 신호 탐지
    risk_report = build_risk_report(metrics)

    # 3. PBC 추천
    pbc_report = build_pbc_report(risk_report)

    # 4. 기존 분석 결과와 비교
    old_path = OUTPUT_DIR / "audit_risk_report.csv"

    if old_path.exists():
        old_report = pd.read_csv(
            old_path, encoding="utf-8-sig"
        )

        old_keys = set(zip(
            old_report["기업"], old_report["규칙"]
        ))
        new_keys = set(zip(
            risk_report["기업"], risk_report["규칙"]
        ))

        if old_keys != new_keys:
            raise AssertionError(
                f"탐지 결과 차이: "
                f"기존에만 있음={old_keys - new_keys}, "
                f"신규에만 있음={new_keys - old_keys}"
            )

        print("기존 탐지 결과와 비교 검증 통과")

    # 5. 분석 결과 저장
    metrics.to_csv(
        OUTPUT_DIR / "engine_inputs_2025.csv",
        index=False, encoding="utf-8-sig"
    )

    risk_report.to_csv(
        OUTPUT_DIR / "audit_risk_report_final.csv",
        index=False, encoding="utf-8-sig"
    )

    pbc_report.to_csv(
        OUTPUT_DIR / "pbc_request_list_final.csv",
        index=False, encoding="utf-8-sig"
    )

    print("분석 기업:", len(metrics), "개")
    print("검토 신호:", len(risk_report), "건")
    print("추천 PBC:", len(pbc_report), "건")
    print("최종 보고서 저장 완료!")


if __name__ == "__main__":
    main()
