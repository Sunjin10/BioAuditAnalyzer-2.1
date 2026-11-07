
import argparse
import re
from getpass import getpass
from pathlib import Path

from src.dart_client import (
    get_corp_list,
    find_company,
    get_financial_statements
)

from src.financial_metrics import calculate_metrics

from src.biotech_profile import build_focus_report

from src.biotech_risk import build_biotech_risk_report

from src.biotech_pbc import build_biotech_pbc_report

from src.report_writer import save_company_report


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="BioAuditAnalyzer 2.1 기업별 공시 조회"
    )

    parser.add_argument(
        "--company",
        required=True,
        help="분석할 기업명"
    )

    parser.add_argument(
        "--year",
        type=int,
        default=2025,
        help="사업연도"
    )

    parser.add_argument(
    "--model",
    choices=["unknown", "license", "manufacturing", "mixed"],
    default="unknown",
    help="제약·바이오 사업모델"
    )
    
    args = parser.parse_args(argv)

    # 인증키는 코드에 저장하지 않음
    api_key = getpass("OpenDART API 키 입력: ")

    print("\n기업 정보를 조회합니다.")

    corp_df = get_corp_list(api_key)

    company = find_company(
        corp_df,
        args.company
    )

    print("기업명:", company["corp_name"])
    print("기업고유번호:", company["corp_code"])
    print("종목코드:", company["stock_code"])

    # 재무제표 자동 수집
    fs, fs_div = get_financial_statements(
        api_key,
        company["corp_code"],
        args.year
    )

    print("\n재무제표 수집 성공!")
    print("사업연도:", args.year)
    print(
        "재무제표 기준:",
        "연결" if fs_div == "CFS" else "별도"
    )
    print("수집 계정 수:", len(fs))

    # 파일 저장
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(
        r"[^0-9A-Za-z가-힣_-]+",
        "_",
        company["corp_name"]
    )

    output_path = (
        OUTPUT_DIR /
        f"{safe_name}_{args.year}_{fs_div}_raw.csv"
    )

    fs.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    # 기업별 재무비율 자동 계산
    metrics_df, metric_details = calculate_metrics(
        fs,
        company["corp_name"],
        args.year,
        fs_div,
        with_details=True
    )

    # 사업모델별 검토항목 생성
    focus_df = build_focus_report(
        metrics_df,
        business_model=args.model
    )

    # 검토항목 CSV 저장
    focus_path = (
        OUTPUT_DIR /
        f"{safe_name}_{args.year}_{fs_div}_focus.csv"
    )

    focus_df.to_csv(
        focus_path,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n[사업모델별 중점 검토항목]")
    print(focus_df.to_string(index=False))

    print("\n검토항목 저장 완료:", focus_path)

    # 사업모델을 반영한 검토 신호 탐지
    biotech_risk_df = build_biotech_risk_report(
        metrics_df,
        business_model=args.model
    )

    # 검토 신호 저장
    risk_path = (
        OUTPUT_DIR /
        f"{safe_name}_{args.year}_{fs_div}_risk.csv"
    )

    biotech_risk_df.to_csv(
        risk_path,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n[제약·바이오 검토 신호]")

    if biotech_risk_df.empty:
        print("설정한 탐지 규칙에 해당하는 신호가 없습니다.")
    else:
        print(biotech_risk_df.to_string(index=False))

    print("\n검토 신호 저장 완료:", risk_path)

    
    # 사업모델별 PBC 추천
    biotech_pbc_df = build_biotech_pbc_report(
        biotech_risk_df,
        business_model=args.model
    )

    # PBC 추천 결과 저장
    pbc_path = (
        OUTPUT_DIR /
        f"{safe_name}_{args.year}_{fs_div}_pbc.csv"
    )

    biotech_pbc_df.to_csv(
        pbc_path,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n[사업모델별 PBC 추천]")

    if biotech_pbc_df.empty:
        print("추가 검토 신호에 해당하는 PBC 추천 없음")
    else:
        print(
            biotech_pbc_df[
                [
                    "규칙",
                    "검토우선순위",
                    "추천유형",
                    "요청자료",
                    "적용조건"
                ]
            ].to_string(index=False)
        )

    print("\nPBC 추천 결과 저장 완료:", pbc_path)

    
    # 공시 접수번호 확인
    receipt_no = None

    if "rcept_no" in fs.columns:
        receipts = fs["rcept_no"].dropna()

        if not receipts.empty:
            receipt_no = str(receipts.iloc[0])

    # 기업별 Markdown 보고서 저장
    report_dir = PROJECT_ROOT / "reports"

    report_path = (
        report_dir /
        f"{safe_name}_{args.year}_{fs_div}_report.md"
    )

    save_company_report(
        metrics_df=metrics_df,
        focus_df=focus_df,
        risk_df=biotech_risk_df,
        pbc_df=biotech_pbc_df,
        business_model=args.model,
        output_path=report_path,
        receipt_no=receipt_no,
        metric_details=metric_details
    )

    print("\n기업별 분석 보고서 저장 완료:", report_path)


    # 계산 결과 저장
    metrics_path = (
        OUTPUT_DIR /
        f"{safe_name}_{args.year}_{fs_div}_metrics.csv"
    )

    metrics_df.to_csv(
        metrics_path,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n[자동 계산 재무지표]")
    print(metrics_df.round(2).T.to_string(header=False))

    print("\n재무지표 저장 완료:", metrics_path)

    print("\n저장 완료:", output_path)

    # 주요 계정 일부 출력
    print("\n[재무제표 미리보기]")

    columns = [
        "sj_nm",
        "account_nm",
        "thstrm_amount",
        "frmtrm_amount"
    ]

    print(fs.reindex(columns=columns).head(10).to_string(index=False))

    return company["corp_name"], output_path


if __name__ == "__main__":
    main()
