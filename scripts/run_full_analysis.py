import argparse

from scripts.run_company import main as run_company
from scripts.run_int02 import process_company
from src.int02_integration import merge_int02


def main():
    parser = argparse.ArgumentParser(
        description="BioAuditAnalyzer 2.1 통합 분석"
    )

    parser.add_argument(
        "--company",
        required=True,
        help="분석할 기업명"
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="분석 사업연도"
    )

    parser.add_argument(
        "--model",
        choices=[
            "unknown",
            "license",
            "manufacturing",
            "mixed"
        ],
        default="unknown"
    )

    args = parser.parse_args()

    # 1. 기존 기업 분석 실행
    print("\n[1/3] 기본 재무분석 실행", flush=True)

    company, raw_path = run_company([
        "--company",
        args.company,
        "--year",
        str(args.year),
        "--model",
        args.model
    ])

    # 2. 무형자산 변동 분석 및 보고서 반영
    print("\n[2/3] INT-02 분석 실행", flush=True)

    screen_path = process_company(
        company, args.year, raw_path=raw_path
    )

    print("\n[3/3] INT-02 위험·PBC 통합", flush=True)

    merge_int02(
        company,
        args.year,
        business_model=args.model,
        screen_path=screen_path
    )

    print("\nBioAuditAnalyzer 통합 분석 완료!")


if __name__ == "__main__":
    main()
