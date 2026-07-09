"""detailIntro2 는 contentTypeId 마다 필드명이 다르다. 타입별 (라벨, 키) 매핑."""
from __future__ import annotations

INTRO_FIELDS: dict[str, list[tuple[str, str]]] = {
    "12": [("운영시간", "usetime"), ("휴무일", "restdate"), ("주차", "parking"), ("문의", "infocenter")],
    "14": [("운영시간", "usetimeculture"), ("휴무일", "restdateculture"), ("주차", "parkingculture"), ("문의", "infocenterculture")],
    "15": [("공연시간", "playtime"), ("이용요금", "usetimefestival"), ("장소", "eventplace"), ("문의", "sponsor1tel")],
    "28": [("운영시간", "usetimeleports"), ("휴무일", "restdateleports"), ("주차", "parkingleports"), ("문의", "infocenterleports")],
    "32": [("체크인", "checkintime"), ("체크아웃", "checkouttime"), ("객실유형", "roomtype"), ("주차", "parkinglodging"), ("문의", "infocenterlodging")],
    "38": [("운영시간", "opentime"), ("휴무일", "restdateshopping"), ("주차", "parkingshopping"), ("문의", "infocentershopping")],
    "39": [("운영시간", "opentimefood"), ("휴무일", "restdatefood"), ("대표메뉴", "firstmenu"), ("주차", "parkingfood"), ("문의", "infocenterfood")],
}


def extract_operating(content_type_id: str | None, intro: dict | None) -> list[tuple[str, str]]:
    if not intro or not content_type_id:
        return []
    rows = []
    for label, key in INTRO_FIELDS.get(content_type_id, []):
        value = (intro.get(key) or "").strip()
        if value:
            rows.append((label, value))
    return rows
