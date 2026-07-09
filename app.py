"""
🐾 PetPass — 반려동물 동반여행 조건 확인 (Streamlit)

내 반려견의 견종·무게 조건과 목적지의 실제 출입 규정(한국관광공사 KorPetTourService2)을
자동 대조해 현장 입장 거부·헛걸음을 예방하는 웹앱.

실행: streamlit run app.py   (.env 에 KTO_SERVICE_KEY=디코딩키 필요)
"""
from __future__ import annotations

from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

from petpass import store
from petpass.constants import (
    CONTENT_TYPES,
    REGIONS,
    SIZE_DEFAULT_WEIGHT,
    SIZE_LABEL,
)
from petpass.intro_fields import extract_operating
from petpass.kto import (
    KtoError,
    area_based_list,
    detail_all,
    location_based_list,
    pet_tours_bulk,
    search_keyword,
    signgu_list,
)
from petpass.match import Judgment, judge
from petpass.textutil import extract_url, format_modified, split_free, strip_html

st.set_page_config(page_title="PetPass", page_icon="🐾", layout="wide")

BANNER = Path(__file__).parent / "assets" / "banner.png"

# Material 3 "kawaii" 디자인 (와인 primary + 핑크 컨테이너 + 둥근/알약 + Quicksand)
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;700&display=swap');

/* 폰트 전역 적용 */
html, body, button, input, select, textarea,
[data-testid="stAppViewContainer"], section[data-testid="stSidebar"],
.stMarkdown, [class*="st-"] {
    font-family: 'Quicksand','Noto Sans KR',sans-serif !important;
}
[data-testid="stAppViewContainer"] { background: #f8f9fa; }

/* 제목 — 와인색 */
h1, h2 { color: #864d61 !important; letter-spacing: -0.5px; }

/* 페이지 헤더 (목업의 큰 제목 + 부제) */
.pp-title { font-size: 2.6rem; font-weight: 700; color: #864d61;
    letter-spacing: -1px; line-height: 1.15; margin: 0.2rem 0 0.2rem; }
.pp-subtitle { font-size: 1.05rem; color: #8a7b7f; margin: 0 0 0.4rem; }

/* 사이드바 섹션 라벨 (MAIN MENU) */
.pp-menu-label { font-size: 0.72rem; font-weight: 700; letter-spacing: 1.5px;
    color: #b79aa3; margin: 0.4rem 0 0.2rem 0.6rem; }

/* 결과 헤더 (검색 결과 N곳 / 추천순) */
.pp-results-head { font-size: 1.25rem; font-weight: 700; color: #191c1d; }
.pp-results-head b { color: #864d61; }
.pp-sort { color: #8a7b7f; font-size: 0.9rem; font-weight: 600; }

/* 지도(iframe) — 두꺼운 흰 테두리 + 둥근 + kawaii 그림자 */
iframe[title="streamlit_folium.st_folium"], iframe[title="st_folium"] {
    border-radius: 24px !important;
    border: 8px solid #ffffff !important;
    box-shadow: 0 10px 25px -5px rgba(134,77,97,0.18) !important;
}

/* 카드(테두리 컨테이너) — 크게 둥글게 + kawaii 그림자 */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 24px !important;
    border-color: #eadde0 !important;
    box-shadow: 0 10px 25px -5px rgba(134,77,97,0.10), 0 8px 10px -6px rgba(134,77,97,0.05);
    background: #ffffff;
}

/* 기본 버튼 — 알약 */
.stButton > button, .stFormSubmitButton > button {
    border-radius: 999px !important; font-weight: 700 !important;
    border: 1.5px solid #f3d9e0 !important;
}
.stButton > button:hover, .stFormSubmitButton > button:hover { border-color: #864d61 !important; }

/* 셀렉트박스 — 둥근 사각 + 테두리 */
div[data-baseweb="select"] > div {
    border-radius: 16px !important; border: 2px solid #d5c2c6 !important; background: #fff !important;
}
/* 배너 이미지 둥근 모서리 */
div[data-testid="stImage"] img { border-radius: 24px; }

/* 사이드바 — 그라디언트 */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#ffffff 0%,#fff0f3 100%) !important;
}
/* 사이드바 네비게이션 메뉴 아이템 */
section[data-testid="stSidebar"] .stButton > button {
    justify-content: flex-start !important; text-align: left !important;
    border: none !important; background: transparent !important;
    border-radius: 999px !important; padding: 0.6rem 1rem !important;
    font-weight: 700 !important; color: #514347 !important; box-shadow: none !important;
}
section[data-testid="stSidebar"] .stButton > button:hover { background: #ffe3ef !important; color: #864d61 !important; }
/* 활성 메뉴: 핑크 컨테이너 + 글로우 */
section[data-testid="stSidebar"] .stButton > button[kind="primary"],
section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
    background: #ffb7ce !important; color: #7b4458 !important;
    box-shadow: 0 0 15px rgba(255,183,206,0.6) !important;
}

/* 유형 토글 버튼 — active=핑크 컨테이너 / inactive=흰색 */
div[class*="st-key-t_"] button {
    border-radius: 999px !important; font-weight: 600 !important;
    padding: 0.4rem 0.2rem !important;
}
div[class*="st-key-t_"] button[kind="primary"], div[class*="st-key-t_"] button[data-testid="stBaseButton-primary"] {
    background: #ffb7ce !important; color: #7b4458 !important; border: none !important;
}
div[class*="st-key-t_"] button[kind="secondary"], div[class*="st-key-t_"] button[data-testid="stBaseButton-secondary"] {
    background: #ffffff !important; color: #514347 !important; border: 1px solid #eadde0 !important;
}

/* 판정 필터 — 목업 색 (초록/주황/빨강), 크고 두툼한 알약 버튼 */
.st-key-vf_ok button, .st-key-vf_conditional button, .st-key-vf_no button {
    border-radius: 999px !important; min-height: 3.1rem !important;
    font-size: 1.05rem !important; font-weight: 700 !important;
}
.st-key-vf_ok button[kind="primary"], .st-key-vf_ok button[data-testid="stBaseButton-primary"] { background:#2ecc71 !important; color:#fff !important; border:none !important; }
.st-key-vf_ok button[kind="secondary"], .st-key-vf_ok button[data-testid="stBaseButton-secondary"] { background:#e8f8ef !important; color:#1e9e5a !important; border:1.5px solid #2ecc71 !important; }
.st-key-vf_conditional button[kind="primary"], .st-key-vf_conditional button[data-testid="stBaseButton-primary"] { background:#f39c12 !important; color:#fff !important; border:none !important; }
.st-key-vf_conditional button[kind="secondary"], .st-key-vf_conditional button[data-testid="stBaseButton-secondary"] { background:#fef4e3 !important; color:#c87f0a !important; border:1.5px solid #f39c12 !important; }
.st-key-vf_no button[kind="primary"], .st-key-vf_no button[data-testid="stBaseButton-primary"] { background:#e74c3c !important; color:#fff !important; border:none !important; }
.st-key-vf_no button[kind="secondary"], .st-key-vf_no button[data-testid="stBaseButton-secondary"] { background:#fdeceb !important; color:#c0392b !important; border:1.5px solid #e74c3c !important; }

/* 카드 제목(지도 포커스) 버튼 — 링크처럼 */
div[class*="st-key-title_"] button {
    border: none !important; background: transparent !important;
    padding: 0 !important; font-weight: 700 !important; font-size: 1.05rem !important;
    color: #191c1d !important; text-align: left !important; justify-content: flex-start !important;
    box-shadow: none !important; min-height: 0 !important;
}
div[class*="st-key-title_"] button:hover { color: #864d61 !important; text-decoration: underline; }
</style>
"""

_SIZE_KEYS = ["small", "medium", "large"]
_TYPE_NAMES = {code: name for code, name in CONTENT_TYPES}
# 사이드바 네비게이션 — 목업: 영문 라벨 + 아이콘
_MODE_LABELS = {"지역별": "📍 Region", "검색": "🔍 Search", "내 주변": "🧭 Nearby"}
# 배지 — 목업 팔레트 (솔리드 + 흰 글씨)
_BADGE_COLORS = {
    "ok": ("#2ecc71", "#ffffff"),
    "conditional": ("#f39c12", "#ffffff"),
    "no": ("#e74c3c", "#ffffff"),
}


# ── 상태 초기화 ───────────────────────────────────────────────────────
def _init_state() -> None:
    if "profiles" not in st.session_state:
        st.session_state.profiles = store.load_profiles()
    if "active_id" not in st.session_state:
        profs = st.session_state.profiles
        st.session_state.active_id = profs[0]["id"] if profs else None
    if "view" not in st.session_state:
        st.session_state.view = "list"
    if "detail" not in st.session_state:
        st.session_state.detail = None  # (content_id, content_type_id)
    if "mode" not in st.session_state:
        st.session_state.mode = "지역별"
    if "sel_types" not in st.session_state:
        st.session_state.sel_types = [c for c, _ in CONTENT_TYPES]  # 기본 전체
    if "verdict_filter" not in st.session_state:
        st.session_state.verdict_filter = ["ok", "conditional", "no"]  # 기본 전부
    if "focus_id" not in st.session_state:
        st.session_state.focus_id = None  # 지도에서 강조할 장소


def _active_profile() -> dict | None:
    for p in st.session_state.profiles:
        if p["id"] == st.session_state.active_id:
            return p
    return None


def _persist() -> None:
    store.save_profiles(st.session_state.profiles)


# ── 콜백 ──────────────────────────────────────────────────────────────
def _go_detail(content_id: str, content_type_id: str) -> None:
    st.session_state.view = "detail"
    st.session_state.detail = (content_id, content_type_id)


def _go_list() -> None:
    st.session_state.view = "list"
    st.session_state.detail = None


def _set_mode(m: str) -> None:
    st.session_state.mode = m


_ALL_TYPE_CODES = [c for c, _ in CONTENT_TYPES]


def _toggle_all_types() -> None:
    # 전체 활성(=모든 개별 선택)이면 전부 해제, 아니면 전부 선택
    if set(st.session_state.sel_types) == set(_ALL_TYPE_CODES):
        st.session_state.sel_types = []
    else:
        st.session_state.sel_types = list(_ALL_TYPE_CODES)


def _toggle_type(code: str) -> None:
    cur = st.session_state.sel_types
    if set(cur) == set(_ALL_TYPE_CODES):
        # 전체 활성 상태에서 개별 클릭 → 그 항목만 선택
        st.session_state.sel_types = [code]
    elif code in cur:
        st.session_state.sel_types = [c for c in cur if c != code]
    else:
        st.session_state.sel_types = cur + [code]


def _toggle_verdict(v: str) -> None:
    cur = st.session_state.verdict_filter
    if v in cur:
        st.session_state.verdict_filter = [x for x in cur if x != v]
    else:
        st.session_state.verdict_filter = cur + [v]


def _focus_place(cid: str) -> None:
    st.session_state.focus_id = cid


# ── 렌더 헬퍼 ─────────────────────────────────────────────────────────
def _badge_html(j: Judgment) -> str:
    bg, fg = _BADGE_COLORS[j.verdict]
    label = j.label
    if j.verdict == "conditional" and j.requirements:
        label = f"조건부 · {j.requirements[0]}"
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 10px;'
        f'border-radius:999px;font-size:0.8rem;font-weight:600;white-space:nowrap;">'
        f"{j.emoji} {label}</span>"
    )


def _render_map(items: list[dict]) -> None:
    """결과 장소들을 folium 지도에 마커로 표시. 포커스된 장소는 중심 이동 + 강조."""
    pts = []
    for it in items:
        try:
            lat, lng = float(it.get("mapy")), float(it.get("mapx"))
        except (TypeError, ValueError):
            continue
        if lat and lng:
            pts.append((lat, lng, it.get("title", ""), it.get("contentid")))
    if not pts:
        return

    focus_id = st.session_state.get("focus_id")
    focus_pt = next((p for p in pts if p[3] == focus_id), None)

    center = [sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)]
    m = folium.Map(location=center, zoom_start=12)
    for lat, lng, title, cid in pts:
        if cid == focus_id:
            folium.Marker(
                [lat, lng], tooltip=title, popup=title,
                icon=folium.Icon(color="red", icon="star", prefix="fa"),
            ).add_to(m)
        else:
            folium.Marker([lat, lng], tooltip=title).add_to(m)

    if not focus_pt and len(pts) > 1:
        lats = [p[0] for p in pts]
        lngs = [p[1] for p in pts]
        m.fit_bounds([[min(lats), min(lngs)], [max(lats), max(lngs)]])

    # 포커스가 있으면 st_folium 의 center/zoom 으로 그 장소로 이동
    kwargs = {}
    if focus_pt:
        kwargs = {"center": [focus_pt[0], focus_pt[1]], "zoom": 16}
    st_folium(m, height=300, use_container_width=True, returned_objects=[],
              key="resultmap", **kwargs)


def _format_distance(dist) -> str | None:
    try:
        m = float(dist)
    except (TypeError, ValueError):
        return None
    if m <= 0:
        return None
    return f"{m/1000:.1f}km" if m >= 1000 else f"{round(m)}m"


# ── 온보딩 / 프로필 폼 ────────────────────────────────────────────────
def _profile_form(key_prefix: str, initial: dict | None = None) -> dict | None:
    """프로필 입력 폼. 제출되면 dict 반환, 아니면 None."""
    with st.form(f"{key_prefix}_form"):
        name = st.text_input("반려견 이름", value=initial.get("name", "") if initial else "")
        size = st.radio(
            "크기",
            _SIZE_KEYS,
            index=_SIZE_KEYS.index(initial["size"]) if initial else 0,
            format_func=lambda s: SIZE_LABEL[s],
            horizontal=True,
        )
        weight = st.slider(
            "몸무게 (kg)",
            1, 80,
            value=int(initial["weightKg"]) if initial else SIZE_DEFAULT_WEIGHT[size],
        )
        is_danger = st.toggle(
            "맹견 여부 (도사견·핏불 등 법정 맹견)",
            value=bool(initial["isDangerBreed"]) if initial else False,
        )
        submitted = st.form_submit_button("저장")
        if submitted:
            if not name.strip():
                st.warning("이름을 입력하세요.")
                return None
            return {
                "name": name.strip(),
                "size": size,
                "weightKg": weight,
                "isDangerBreed": is_danger,
            }
    return None


def _render_onboarding() -> None:
    st.markdown("### 🐾 PetPass 시작하기")
    st.caption("반려견 정보를 등록하면, 가려는 곳의 출입 규정과 자동으로 대조해 드려요.")
    result = _profile_form("onboarding")
    if result:
        prof = store.new_profile(result["name"], result["size"], result["weightKg"], result["isDangerBreed"])
        st.session_state.profiles.append(prof)
        st.session_state.active_id = prof["id"]
        _persist()
        st.rerun()


# ── 프로필 팝오버 (우측 상단, 이름 클릭 → 바로 수정) ──────────────────
def _render_profile_popover() -> None:
    ap = _active_profile()
    label = f"🐶 {ap['name']}" if ap else "🐶 프로필"
    with st.popover(label, use_container_width=True):
        profs = st.session_state.profiles
        ids = [p["id"] for p in profs]
        labels = {p["id"]: p["name"] for p in profs}

        # 반려견이 여러 마리면 전환 셀렉트
        if len(profs) > 1:
            active = st.selectbox(
                "반려견 선택",
                ids,
                index=ids.index(st.session_state.active_id) if st.session_state.active_id in ids else 0,
                format_func=lambda i: labels.get(i, "?"),
                key="active_sel",
            )
            if active != st.session_state.active_id:
                st.session_state.active_id = active
                st.rerun()

        # 활성 반려견 정보를 바로 수정 (저장 시 즉시 반영 + 배지 재계산)
        if ap:
            st.markdown("**✏️ 정보 수정**")
            result = _profile_form("edit", ap)
            if result:
                ap.update(result)
                _persist()
                st.rerun()
            if len(profs) > 1 and st.button("🗑️ 이 반려견 삭제", key="del"):
                st.session_state.profiles = [p for p in profs if p["id"] != ap["id"]]
                st.session_state.active_id = st.session_state.profiles[0]["id"]
                _persist()
                st.rerun()

        with st.expander("➕ 새 반려견 추가"):
            result = _profile_form("add")
            if result:
                prof = store.new_profile(result["name"], result["size"], result["weightKg"], result["isDangerBreed"])
                st.session_state.profiles.append(prof)
                st.session_state.active_id = prof["id"]
                _persist()
                st.rerun()


# ── 상단바 (우측 프로필 + 작은 배너 이미지) ───────────────────────────
def _render_topbar() -> None:
    _, right = st.columns([5, 1], vertical_alignment="center")
    with right:
        _render_profile_popover()


# ── 사이드바 (좌측 네비게이션 메뉴) ───────────────────────────────────
def _render_sidebar() -> str:
    st.sidebar.markdown("## 🐾 PetPass")
    st.sidebar.caption("반려동물 동반여행 조건 확인")
    st.sidebar.markdown("")
    st.sidebar.markdown("<div class='pp-menu-label'>MAIN MENU</div>", unsafe_allow_html=True)

    for m in ["지역별", "검색", "내 주변"]:
        active = st.session_state.mode == m
        st.sidebar.button(
            _MODE_LABELS[m],
            key=f"nav_{m}",
            use_container_width=True,
            type="primary" if active else "secondary",
            on_click=_set_mode,
            args=(m,),
        )

    return st.session_state.mode


# ── 목록 결과 렌더 ────────────────────────────────────────────────────
def _render_card(it: dict, j: Judgment) -> None:
    cid = it["contentid"]
    focused = st.session_state.get("focus_id") == cid
    with st.container(border=True):
        c1, c2 = st.columns([1, 3], vertical_alignment="center")
        with c1:
            img = it.get("firstimage")
            if img:
                st.image(img, width="stretch")
            else:
                st.markdown("<div style='font-size:2.4rem;text-align:center'>🐾</div>", unsafe_allow_html=True)
        with c2:
            # 제목 클릭 = 지도 포커스 (상세 이동 아님)
            title = ("📍 " if focused else "") + it.get("title", "")
            st.button(title, key=f"title_{cid}", use_container_width=True,
                      on_click=_focus_place, args=(cid,), help="클릭하면 지도에서 위치를 보여줍니다")
            dist = _format_distance(it.get("dist"))
            addr = it.get("addr1", "")
            st.caption((f"📍 {dist} · " if dist else "") + addr)
            st.markdown(_badge_html(j), unsafe_allow_html=True)
            if j.reasons:
                st.caption(j.reasons[0])
            # 자세히 보기 = 상세 페이지 이동
            st.button("자세히 보기 →", key=f"d_{cid}", on_click=_go_detail, args=(cid, it.get("contenttypeid", "")))


def _render_results(items: list[dict]) -> None:
    profile = _active_profile()
    if not items:
        st.info("조건에 맞는 장소가 없어요. 다른 조건으로 시도해 보세요.")
        return

    content_ids = [it["contentid"] for it in items]
    with st.spinner("동반 조건을 확인하는 중…"):
        pet_map = pet_tours_bulk(content_ids)
    judgments = {cid: judge(profile, pet_map.get(cid)) for cid in content_ids}

    # 판정 결과 필터 적용
    vf = st.session_state.get("verdict_filter", ["ok", "conditional", "no"])
    visible = [it for it in items if judgments[it["contentid"]].verdict in vf]

    if not visible:
        st.info("선택한 판정 필터에 해당하는 장소가 없어요. 상단 필터를 확인하세요.")
        return

    # 좌: 목록 / 우: 지도
    col_list, col_map = st.columns([3, 2], gap="large")
    with col_list:
        head_l, head_r = st.columns([3, 1], vertical_alignment="bottom")
        head_l.markdown(
            f"<div class='pp-results-head'>검색 결과 <b>{len(visible)}곳</b></div>",
            unsafe_allow_html=True,
        )
        head_r.markdown(
            "<div class='pp-sort' style='text-align:right'>≡ 추천순</div>",
            unsafe_allow_html=True,
        )
        for it in visible:
            _render_card(it, judgments[it["contentid"]])
    with col_map:
        _render_map(visible)
        st.caption("카드 제목을 누르면 지도에서 위치를 강조합니다.")


# ── 여러 유형을 조회해 병합 ───────────────────────────────────────────
def _multi_fetch(per_type, type_ids: list[str], sort_by_dist: bool = False) -> list[dict]:
    """선택된 유형별로 per_type(tid) 를 호출해 contentid 중복 없이 병합."""
    items: list[dict] = []
    seen: set[str] = set()
    last_err: KtoError | None = None
    for tid in type_ids:
        try:
            its, _ = per_type(tid)
        except KtoError as e:
            last_err = e
            continue
        for it in its:
            cid = it.get("contentid")
            if cid and cid not in seen:
                seen.add(cid)
                items.append(it)
    if sort_by_dist:
        def _d(it):
            try:
                return float(it.get("dist"))
            except (TypeError, ValueError):
                return float("inf")
        items.sort(key=_d)
    if last_err and not items:
        st.error(f"불러오지 못했습니다: [{last_err.code}] {last_err.message}")
    return items


# ── 유형 다중 토글 버튼 ('전체' ↔ 개별 상호배타) ──────────────────────
def _render_type_toggles() -> list[str] | None:
    """토글 버튼 렌더 후 조회용 유형 리스트 반환. '전체'면 [""], 없으면 None."""
    is_all = set(st.session_state.sel_types) == set(_ALL_TYPE_CODES)

    cols = st.columns(len(CONTENT_TYPES) + 1)
    cols[0].button(
        "전체",
        key="t_all",
        use_container_width=True,
        type="primary" if is_all else "secondary",
        on_click=_toggle_all_types,
    )
    for i, (code, name) in enumerate(CONTENT_TYPES):
        active = code in st.session_state.sel_types
        cols[i + 1].button(
            name,
            key=f"t_{code}",
            use_container_width=True,
            type="primary" if active else "secondary",
            on_click=_toggle_type,
            args=(code,),
        )

    sel = st.session_state.sel_types
    if not sel:
        st.info("유형을 하나 이상 선택하세요.")
        return None
    # 전체 = 유형 필터 없이 한 번에 조회
    return [""] if set(sel) == set(_ALL_TYPE_CODES) else sel


# ── 판정 결과 필터 (가능/조건부/불가, 배지색과 동일) ──────────────────
def _render_verdict_filter() -> None:
    meta = [("ok", "● 가능"), ("conditional", "● 조건부"), ("no", "● 불가")]
    cols = st.columns(3)
    for i, (v, label) in enumerate(meta):
        active = v in st.session_state.verdict_filter
        cols[i].button(
            label,
            key=f"vf_{v}",
            use_container_width=True,
            type="primary" if active else "secondary",
            on_click=_toggle_verdict,
            args=(v,),
        )


# ── 목록 화면 (모드는 사이드바에서 전달) ──────────────────────────────
def _render_list(mode: str) -> None:
    st.markdown(
        "<div class='pp-title'>반려동물 동반여행</div>"
        "<div class='pp-subtitle'>우리 아이와 함께할 수 있는 최적의 장소를 찾아보세요.</div>",
        unsafe_allow_html=True,
    )
    type_ids = _render_type_toggles()
    if type_ids is None:
        return

    _render_verdict_filter()
    st.divider()

    if mode == "지역별":
        col_a, col_b = st.columns(2)
        region = col_a.selectbox("시/도", REGIONS, format_func=lambda t: t[1], key="region")
        try:
            signgus = sorted(signgu_list(region[0]), key=lambda t: t[1])  # 가나다순
        except KtoError:
            signgus = []
        signgu = col_b.selectbox(
            "시/군/구", [("", "전체")] + signgus, format_func=lambda t: t[1], key="signgu"
        )
        items = _multi_fetch(lambda tid: area_based_list(region[0], tid, signgu[0]), type_ids)
        _render_results(items)

    elif mode == "검색":
        with st.form("search_form"):
            keyword = st.text_input("장소명 검색", placeholder="예: 해수욕장")
            go = st.form_submit_button("검색")
        if go and keyword.strip():
            items = _multi_fetch(lambda tid: search_keyword(keyword.strip(), tid), type_ids)
            _render_results(items)
        elif not go:
            st.caption("가고 싶은 장소를 검색해 보세요.")

    else:  # 내 주변
        st.caption("아래 버튼을 눌러 현재 위치를 허용하면 반경 20km를 거리순으로 보여줍니다.")
        try:
            from streamlit_geolocation import streamlit_geolocation
            loc = streamlit_geolocation()
        except Exception:
            loc = None
        if loc and loc.get("latitude") and loc.get("longitude"):
            items = _multi_fetch(
                lambda tid: location_based_list(loc["longitude"], loc["latitude"], tid),
                type_ids,
                sort_by_dist=True,
            )
            _render_results(items)


# ── 상세 화면 ─────────────────────────────────────────────────────────
def _render_detail() -> None:
    content_id, content_type_id = st.session_state.detail
    st.button("← 목록으로", on_click=_go_list)

    with st.spinner("상세 정보를 불러오는 중…"):
        common, intro, pet = detail_all(content_id, content_type_id)

    if not common:
        st.error("상세 정보를 불러오지 못했습니다.")
        return

    profile = _active_profile()
    j = judge(profile, pet)

    img = common.get("firstimage")
    if img:
        st.image(img, width=360)

    st.markdown(f"## {common.get('title','')}")
    if common.get("addr1"):
        st.caption(common["addr1"])
    st.markdown(_badge_html(j), unsafe_allow_html=True)

    # 지도
    try:
        lat, lng = float(common.get("mapy")), float(common.get("mapx"))
        if lat and lng:
            m = folium.Map(location=[lat, lng], zoom_start=16)
            folium.Marker([lat, lng], popup=common.get("title", "")).add_to(m)
            st_folium(m, height=280, use_container_width=True, returned_objects=[])
    except (TypeError, ValueError):
        pass

    # 개요
    overview = strip_html(common.get("overview"))
    if overview:
        st.markdown("#### 개요")
        st.write(overview)

    # 운영 정보
    operating = extract_operating(content_type_id, intro)
    homepage = extract_url(common.get("homepage"))
    if operating or homepage:
        st.markdown("#### 운영 정보")
        for label, value in operating:
            st.markdown(f"**{label}** · {value}")
        if homepage:
            st.markdown(f"**홈페이지** · [{homepage}]({homepage})")

    # 반려동물 조건
    st.markdown("#### 🐶 반려동물 동반 조건")
    if pet:
        if pet.get("acmpyTypeCd"):
            st.markdown(f"**동반유형** · {pet['acmpyTypeCd']}")
        if pet.get("acmpyPsblCpam"):
            st.markdown(f"**가능 견종** · {pet['acmpyPsblCpam']}")
    else:
        st.info("등록된 동반 조건 정보가 없습니다. 방문 전 현장에 직접 확인하세요.")

    if j.reasons:
        msg = f"{profile['name']} 기준 판정: {j.emoji} {j.label}\n\n- " + "\n- ".join(j.reasons)
        if j.verdict == "ok":
            st.success(msg)
        elif j.verdict == "conditional":
            st.warning(msg)
        else:
            st.error(msg)

    # 준비물 체크리스트 + 현장 이용
    if pet:
        checklist = list(dict.fromkeys(
            (j.requirements or [])
            + split_free(pet.get("acmpyNeedMtr"), comma=True)
            + split_free(pet.get("etcAcmpyInfo"))
            + split_free(pet.get("relaAcdntRiskMtr"))
        ))
        if checklist:
            st.markdown("#### ✅ 준비물 체크리스트")
            for i, item in enumerate(checklist):
                st.checkbox(item, key=f"chk_{content_id}_{i}")

        onsite = [
            ("구비 시설", split_free(pet.get("relaPosesFclty"), comma=True)),
            ("비치 품목", split_free(pet.get("relaFrnshPrdlst"), comma=True)),
            ("렌탈 품목", split_free(pet.get("relaRntlPrdlst"), comma=True)),
            ("구매 품목", split_free(pet.get("relaPurcPrdlst"), comma=True)),
        ]
        onsite = [(lab, its) for lab, its in onsite if its]
        if onsite:
            st.markdown("#### 현장에서 이용 가능")
            for lab, its in onsite:
                st.markdown(f"**{lab}** · {', '.join(its)}")

    # 면책 + 수정일
    st.divider()
    if common.get("modifiedtime"):
        st.caption(f"정보 수정일: {format_modified(common['modifiedtime'])}")
    st.caption("조건 판정은 참고 정보이며, 최종 입장 여부는 현장 규정을 따릅니다. 방문 전 매장 확인을 권장합니다.")


# ── 메인 ──────────────────────────────────────────────────────────────
def main() -> None:
    _init_state()
    st.markdown(_CSS, unsafe_allow_html=True)

    if not st.session_state.profiles:
        if BANNER.exists():
            c = st.columns([1, 2, 1])
            with c[1]:
                st.image(str(BANNER), width="stretch")
        _render_onboarding()
        return

    mode = _render_sidebar()
    _render_topbar()

    if st.session_state.view == "detail" and st.session_state.detail:
        _render_detail()
    else:
        _render_list(mode)


main()
