"""
한국관광공사 KorPetTourService2 클라이언트 (Python).

Streamlit 은 서버(Python)에서 API를 직접 호출하므로 프록시가 필요 없다.
- 인증키(KTO_SERVICE_KEY, 디코딩 원본)는 .env 에서만 읽는다 → 브라우저에 노출 안 됨.
- requests 가 파라미터를 URL-인코딩하므로 디코딩 원본 키를 그대로 넘기면 된다.
- @st.cache_data 로 응답을 캐싱해 Streamlit 재실행마다 재호출하지 않는다(콜 한도 절약).
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BASE = "http://apis.data.go.kr/B551011/KorPetTourService2"


class KtoError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _service_key() -> str:
    # 로컬(.env) → Streamlit Cloud(Secrets) 순으로 조회
    key = os.getenv("KTO_SERVICE_KEY", "").strip()
    if not key:
        try:
            key = str(st.secrets["KTO_SERVICE_KEY"]).strip()
        except Exception:
            key = ""
    if not key:
        raise KtoError(
            "NO_KEY",
            "KTO_SERVICE_KEY 가 설정되어 있지 않습니다. (로컬: .env / 배포: Streamlit Secrets)",
        )
    return key


_MESSAGES = {
    "30": "등록되지 않은 인증키입니다. .env 의 KTO_SERVICE_KEY 를 확인하세요.",
    "31": "활용 기간이 만료된 인증키입니다.",
    "22": "일일 호출 한도를 초과했습니다. 잠시 후 다시 시도하세요.",
}


def _request(operation: str, params: dict[str, Any]) -> dict:
    """공통 필수 파라미터를 붙여 요청하고 JSON dict 을 돌려준다."""
    full = {
        "serviceKey": _service_key(),
        "MobileOS": "ETC",
        "MobileApp": "PetPass",
        "_type": "json",
        **{k: v for k, v in params.items() if v not in (None, "")},
    }
    try:
        res = requests.get(f"{BASE}/{operation}", params=full, timeout=15)
    except requests.RequestException:
        raise KtoError("NETWORK", "네트워크 오류로 요청에 실패했습니다.")

    if res.status_code != 200:
        raise KtoError(f"HTTP_{res.status_code}", f"서버 오류 (HTTP {res.status_code})")

    try:
        data = res.json()
    except ValueError:
        raise KtoError("PARSE", "응답을 해석할 수 없습니다. (인증키/파라미터 확인)")

    # 게이트웨이 레벨 에러 (키 오류 등)
    gw = data.get("OpenAPI_ServiceResponse")
    if gw:
        h = gw.get("cmmMsgHeader", {})
        code = str(h.get("returnReasonCode", "GATEWAY"))
        raise KtoError(code, _MESSAGES.get(code, h.get("errMsg", "게이트웨이 오류")))

    header = data.get("response", {}).get("header", {})
    code = str(header.get("resultCode", ""))
    if code == "":
        raise KtoError("UNKNOWN", "예상치 못한 응답 형식입니다.")
    # 03 = NODATA → 정상 빈 결과
    if code not in ("0000", "03"):
        raise KtoError(code, _MESSAGES.get(code, header.get("resultMsg", "알 수 없는 오류")))

    return data


def _items(data: dict) -> list[dict]:
    body = data.get("response", {}).get("body", {})
    raw = body.get("items", "")
    if not raw or raw == "":
        return []
    item = raw.get("item")
    if not item:
        return []
    return item if isinstance(item, list) else [item]


def _total(data: dict) -> int:
    return int(data.get("response", {}).get("body", {}).get("totalCount", 0) or 0)


# ── 목록/검색/주변 ───────────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)
def signgu_list(region_code: str) -> list[tuple[str, str]]:
    """시도(lDongRegnCd) 하위 시군구 목록 [(code, name)]. 하루 캐시."""
    data = _request("ldongCode2", {"lDongRegnCd": region_code, "numOfRows": 50, "pageNo": 1})
    rows = []
    for it in _items(data):
        code, name = it.get("code"), it.get("name")
        if code and name:
            rows.append((str(code), name))
    return rows


@st.cache_data(ttl=3600, show_spinner=False)
def area_based_list(region_code: str, content_type_id: str,
                    signgu_code: str = "", num_rows: int = 20) -> tuple[list[dict], int]:
    data = _request("areaBasedList2", {
        "lDongRegnCd": region_code, "lDongSignguCd": signgu_code,
        "contentTypeId": content_type_id,
        "arrange": "C", "numOfRows": num_rows, "pageNo": 1,
    })
    return _items(data), _total(data)


@st.cache_data(ttl=3600, show_spinner=False)
def search_keyword(keyword: str, content_type_id: str, num_rows: int = 20) -> tuple[list[dict], int]:
    data = _request("searchKeyword2", {
        "keyword": keyword, "contentTypeId": content_type_id,
        "arrange": "C", "numOfRows": num_rows, "pageNo": 1,
    })
    return _items(data), _total(data)


@st.cache_data(ttl=600, show_spinner=False)
def location_based_list(map_x: float, map_y: float, content_type_id: str,
                        radius: int = 20000, num_rows: int = 20) -> tuple[list[dict], int]:
    data = _request("locationBasedList2", {
        "mapX": map_x, "mapY": map_y, "radius": radius,
        "contentTypeId": content_type_id, "arrange": "E",
        "numOfRows": num_rows, "pageNo": 1,
    })
    return _items(data), _total(data)


# ── 상세 (contentId 기준, 캐시로 세션 재사용) ─────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def detail_common(content_id: str) -> dict | None:
    items = _items(_request("detailCommon2", {"contentId": content_id}))
    return items[0] if items else None


@st.cache_data(ttl=3600, show_spinner=False)
def detail_intro(content_id: str, content_type_id: str) -> dict | None:
    items = _items(_request("detailIntro2", {
        "contentId": content_id, "contentTypeId": content_type_id,
    }))
    return items[0] if items else None


@st.cache_data(ttl=3600, show_spinner=False)
def detail_pet_tour(content_id: str) -> dict | None:
    items = _items(_request("detailPetTour2", {"contentId": content_id}))
    return items[0] if items else None


def _with_ctx(fn):
    """ThreadPoolExecutor 워커에 Streamlit 스크립트 컨텍스트를 붙여 캐시/경고 문제를 피한다."""
    try:
        from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
        ctx = get_script_run_ctx()

        def wrapped(*args):
            add_script_run_ctx(ctx=ctx)
            return fn(*args)
        return wrapped
    except Exception:
        return fn


def detail_all(content_id: str, content_type_id: str) -> tuple[dict | None, dict | None, dict | None]:
    """detailCommon2·detailIntro2·detailPetTour2 를 병렬 호출 (일부 실패해도 나머지 반환)."""
    def safe(fn, *args):
        try:
            return fn(*args)
        except KtoError:
            return None

    with ThreadPoolExecutor(max_workers=3) as ex:
        f_common = ex.submit(_with_ctx(safe), detail_common, content_id)
        f_intro = ex.submit(_with_ctx(safe), detail_intro, content_id, content_type_id)
        f_pet = ex.submit(_with_ctx(safe), detail_pet_tour, content_id)
        return f_common.result(), f_intro.result(), f_pet.result()


def pet_tours_bulk(content_ids: list[str]) -> dict[str, dict | None]:
    """여러 contentId 의 detailPetTour2 를 병렬 조회 (목록 배지용). 캐시로 재조회 억제."""
    def safe(cid):
        try:
            return detail_pet_tour(cid)
        except KtoError:
            return None

    if not content_ids:
        return {}
    worker = _with_ctx(safe)
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(worker, content_ids))
    return dict(zip(content_ids, results))
