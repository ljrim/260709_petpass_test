"""
반려견 프로필 영속화.

Streamlit 은 브라우저 localStorage 를 직접 못 쓰므로, 로컬 JSON 파일에 저장한다.
(단일 사용자 로컬 실행 기준. 작업 복사본은 session_state 가 들고, 변경 시 파일에 동기화.)
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

_FILE = Path(__file__).resolve().parent.parent / "petpass_data.json"


def load_profiles() -> list[dict]:
    if not _FILE.exists():
        return []
    try:
        data = json.loads(_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (ValueError, OSError):
        return []


def save_profiles(profiles: list[dict]) -> None:
    try:
        _FILE.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def new_profile(name: str, size: str, weight_kg: float, is_danger: bool) -> dict:
    return {
        "id": uuid.uuid4().hex,
        "name": name,
        "size": size,
        "weightKg": weight_kg,
        "isDangerBreed": is_danger,
    }
