import json

import pytest

from core.identity_service import IdentityError, IdentityService


def write_identity(path, **overrides):
    data = {
        "full_name": "Team2050",
        "current_year": 2050,
        "identity_locked": True,
        "birth_date": None,
        "birth_place": None,
        "current_city": None,
        "profession": None,
        "education": None,
        "family": None,
        "communication_origin": None,
    }
    data.update(overrides)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_load_valid_identity(tmp_path):
    path = tmp_path / "system_identity.json"
    write_identity(path)
    service = IdentityService(path)
    data = service.load()
    assert data["full_name"] == "Team2050"
    assert service.initialize_guard()
    assert path.with_suffix(".initial.bak.json").exists()


def test_detects_missing_profile_name(tmp_path):
    path = tmp_path / "system_identity.json"
    write_identity(path, full_name="")
    with pytest.raises(IdentityError, match="не указано имя"):
        IdentityService(path).load()


def test_detects_wrong_year_format(tmp_path):
    path = tmp_path / "system_identity.json"
    write_identity(path, current_year="2050")
    with pytest.raises(IdentityError, match="формат года"):
        IdentityService(path).load()


def test_detects_broken_json(tmp_path):
    path = tmp_path / "system_identity.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(IdentityError, match="неверный JSON"):
        IdentityService(path).load()


def test_detects_identity_change_after_initialization(tmp_path):
    path = tmp_path / "system_identity.json"
    write_identity(path)
    service = IdentityService(path)
    service.initialize_guard()
    write_identity(path, birth_place="не определено")
    assert service.check_for_change()
