
import io
import re
import zipfile
import requests
import pandas as pd
import xml.etree.ElementTree as ET


BASE_URL = "https://opendart.fss.or.kr/api"


def request_dart(url, params):
    """OpenDART 요청. 오류 메시지에 API 키를 노출하지 않는다."""
    try:
        response = requests.get(
            url,
            params=params,
            timeout=45
        )
        response.raise_for_status()
        return response
    except requests.RequestException:
        raise RuntimeError(
            "OpenDART 통신 실패. 인터넷 연결과 API 상태를 확인하세요."
        ) from None


def get_corp_list(api_key):
    """OpenDART에 등록된 기업 목록을 가져온다."""
    response = request_dart(
        f"{BASE_URL}/corpCode.xml",
        {"crtfc_key": api_key}
    )

    content = io.BytesIO(response.content)

    if not zipfile.is_zipfile(content):
        # API 오류는 ZIP이 아닌 XML로 반환될 수 있음
        try:
            root = ET.fromstring(response.content)
            status = root.findtext("status")
            message = root.findtext("message")
            raise RuntimeError(
                f"기업 목록 조회 실패 [{status}]: {message}"
            )
        except ET.ParseError:
            raise RuntimeError("예상하지 못한 API 응답입니다.")

    with zipfile.ZipFile(content) as z:
        xml_name = next(
            name for name in z.namelist()
            if name.lower().endswith(".xml")
        )
        root = ET.fromstring(z.read(xml_name))

    records = [
        {child.tag: child.text for child in item}
        for item in root.findall("list")
    ]

    return pd.DataFrame(records).fillna("")


def normalize_name(name):
    """회사명의 공백과 법인 표기를 정리한다."""
    name = re.sub(r"\s+", "", str(name))
    return (
        name.replace("주식회사", "")
            .replace("(주)", "")
            .replace("㈜", "")
    )



def find_company(corp_df, company_name):
    """기업명으로 기업고유번호를 조회한다."""

    query = normalize_name(company_name)

    if not query:
        raise ValueError("기업명을 입력해야 합니다.")

    normalized = corp_df["corp_name"].map(normalize_name)

    # 1. 기업명이 정확히 일치하는 경우
    matches = corp_df[normalized == query]

    # 2. 정확히 일치하지 않으면 부분 검색
    if matches.empty:
        matches = corp_df[
            normalized.str.contains(
                query, regex=False, na=False
            )
        ]

    if matches.empty:
        raise ValueError(
            f"'{company_name}'에 해당하는 기업이 없습니다."
        )

    # 3. 검색 결과가 1개면 그대로 선택
    if len(matches) == 1:
        return matches.iloc[0].to_dict()

    # 4. 여러 기업이 검색되면 종목코드가 있는 기업 확인
    listed = matches[
        matches["stock_code"].astype(str).str.strip() != ""
    ]

    # 상장 종목코드가 있는 후보가 정확히 1개일 때만 자동 선택
    if len(listed) == 1:
        print("동일 이름의 기업이 여러 개 검색되었습니다.")
        print("종목코드가 있는 기업을 선택합니다.")
        return listed.iloc[0].to_dict()

    # 5. 여전히 구분할 수 없다면 임의로 선택하지 않음
    candidates = matches[
        ["corp_name", "corp_code", "stock_code"]
    ]

    raise ValueError(
        "기업을 하나로 특정할 수 없습니다.\n"
        + candidates.to_string(index=False)
    )



def get_financial_statements(api_key, corp_code, year):
    """사업보고서 연결재무제표를 우선 조회한다."""

    if year < 2015:
        raise ValueError(
            "이 API는 2015년 이후 사업연도를 지원합니다."
        )

    for fs_div in ["CFS", "OFS"]:
        response = request_dart(
            f"{BASE_URL}/fnlttSinglAcntAll.json",
            {
                "crtfc_key": api_key,
                "corp_code": corp_code,
                "bsns_year": str(year),
                "reprt_code": "11011",
                "fs_div": fs_div
            }
        )

        try:
            data = response.json()
        except ValueError:
            raise RuntimeError(
                "재무제표 응답을 JSON으로 변환할 수 없습니다."
            ) from None

        status = data.get("status")

        if status == "000":
            rows = data.get("list", [])
            if rows:
                return pd.DataFrame(rows), fs_div

        elif status != "013":
            raise RuntimeError(
                f"재무제표 조회 실패 [{status}]: "
                f"{data.get('message')}"
            )

    raise ValueError(
        f"{year}년 사업보고서 재무제표를 찾지 못했습니다."
    )
