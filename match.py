"""
조건 판정 파서 (React 버전에서 포팅, 실데이터로 검증한 규칙).

detailPetTour2 자유 텍스트를 정규식으로 파싱해 활성 프로필과 대조.
실패/애매하면 '불가'가 아니라 반드시 🟡 조건부로 폴백한다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

WEIGHT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*kg\s*이하")
ALL_BREEDS_RE = re.compile(r"전\s*견종|모든\s*(?:견종|반려견)")
EXCLUDE_DANGER_RE = re.compile(r"맹견[^.]{0,6}(?:제외|불가|동반\s*불가)")
MUZZLE_FOR_DANGER_RE = re.compile(r"맹견[^.]{0,12}입마개")
MUZZLE_ANY_RE = re.compile(r"입마개")


@dataclass
class Judgment:
    verdict: str  # 'ok' | 'conditional' | 'no'
    emoji: str
    label: str
    reasons: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    has_data: bool = True


def _make(verdict: str, reasons: list[str], requirements: list[str], has_data: bool) -> Judgment:
    meta = {
        "ok": ("🟢", "가능"),
        "no": ("🔴", "불가"),
        "conditional": ("🟡", "조건부"),
    }[verdict]
    return Judgment(verdict, meta[0], meta[1], reasons, requirements, has_data)


def judge(profile: dict, pet: dict | None) -> Judgment:
    """profile: {'name','size','weightKg','isDangerBreed'}, pet: detailPetTour2 item or None."""
    pet = pet or {}
    psbl = (pet.get("acmpyPsblCpam") or "").strip()
    type_cd = (pet.get("acmpyTypeCd") or "").strip()
    etc = (pet.get("etcAcmpyInfo") or "").strip()
    need = (pet.get("acmpyNeedMtr") or "").strip()
    combined = " ".join([psbl, etc, need])

    has_data = bool(psbl or type_cd or etc or need)
    if not has_data:
        return _make("conditional", ["등록된 동반 조건 정보가 없어 직접 확인이 필요합니다."], [], False)

    reasons: list[str] = []
    requirements: list[str] = []

    weight_m = WEIGHT_RE.search(psbl) or WEIGHT_RE.search(etc)
    weight_limit = float(weight_m.group(1)) if weight_m else None
    excludes_danger = bool(EXCLUDE_DANGER_RE.search(combined))
    all_breeds = bool(ALL_BREEDS_RE.search(psbl))
    muzzle_for_danger = bool(MUZZLE_FOR_DANGER_RE.search(combined))
    muzzle_any = bool(MUZZLE_ANY_RE.search(need))

    weight = float(profile.get("weightKg", 0))
    is_danger = bool(profile.get("isDangerBreed"))

    # 규칙 2: 무게 상한 초과 → 🔴
    if weight_limit is not None and weight > weight_limit:
        reasons.append(f"무게 상한 {weight_limit:g}kg 초과 (내 반려견 {weight:g}kg)")
        return _make("no", reasons, requirements, True)

    # 규칙 3: 맹견 프로필 & 맹견 제외/불가 → 🔴
    if is_danger and excludes_danger:
        reasons.append("맹견은 동반 불가로 안내되어 있습니다.")
        return _make("no", reasons, requirements, True)

    # 규칙 4: 입마개 조건 수집
    if is_danger and muzzle_for_danger:
        requirements.append("맹견 입마개 착용 필수")
    if muzzle_any and not requirements:
        requirements.append("입마개 착용 필요")

    # 긍정 사유
    if weight_limit is not None:
        reasons.append(f"무게 상한 {weight_limit:g}kg 이하 충족 (내 반려견 {weight:g}kg)")
    if excludes_danger and not is_danger:
        reasons.append("맹견 외 견종 동반 가능")
    elif all_breeds:
        reasons.append("전 견종 동반 가능")

    clearly_allowed = all_breeds or weight_limit is not None or excludes_danger

    if clearly_allowed:
        if requirements:
            return _make("conditional", reasons, requirements, True)
        return _make("ok", reasons, requirements, True)

    # 규칙 6: 파싱은 됐으나 애매 → 🟡 폴백
    reasons.append("조건 문구가 명확하지 않아 현장 확인이 필요합니다.")
    return _make("conditional", reasons, requirements, True)
