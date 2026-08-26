from pathlib import Path

from core.avatar_catalog import list_avatar_files
from core.employee_identity import _pick_avatar, generate_identity


def test_generated_identity_has_editable_profile_fields_and_avatar(tmp_path):
    (tmp_path / "avatar-01-woman-realistic.png").write_bytes(b"avatar")

    identity = generate_identity("ru", "female", tmp_path)

    assert identity.name
    assert identity.gender == "female"
    assert identity.biography
    assert identity.preferred_name
    assert identity.informal_name
    assert identity.communication_profile["directness"] in range(2, 6)
    assert identity.avatar_path == str(tmp_path / "avatar-01-woman-realistic.png")


def test_generated_identity_supports_all_interface_languages():
    for language in ("ru", "uk", "en"):
        identity = generate_identity(language, "male", None)
        assert identity.name
        assert identity.gender == "male"
        assert identity.biography


def test_avatar_catalog_excludes_source_sheets(tmp_path):
    avatar = tmp_path / "avatar-21-realistic.png"
    avatar.write_bytes(b"avatar")
    (tmp_path / "avatar-sheet-team.png").write_bytes(b"sheet")
    (tmp_path / "notes.txt").write_text("not an image", encoding="utf-8")

    assert list_avatar_files(tmp_path) == [avatar]


def test_bundled_avatar_catalog_has_product_scale():
    avatar_dir = Path(__file__).resolve().parents[1] / "data" / "avatars"
    avatars = list_avatar_files(avatar_dir)

    assert 75 <= len(avatars) <= 100
    assert all("sheet" not in path.stem.lower() for path in avatars)


def test_identity_generator_has_human_scale_variety_and_balanced_origin():
    generated = [generate_identity("en") for _ in range(500)]
    unique_names = {identity.name for identity in generated}
    ukrainian_surnames = {
        "Koval", "Melnyk", "Bondarenko", "Shevchenko", "Kravchenko", "Boiko",
        "Tkachenko", "Romaniuk", "Kozak", "Polishchuk", "Savchenko", "Marchenko",
        "Levchenko", "Ostapenko", "Hrytsenko", "Petrenko",
    }
    ukrainian_count = sum(identity.name.split()[-1] in ukrainian_surnames for identity in generated)

    assert len(unique_names) >= 300
    assert 200 <= ukrainian_count <= 300
    assert all(identity.preferred_name in identity.name for identity in generated)
    forbidden_defaults = {"roman", "petr", "shushan", "shushanna", "vasian"}
    assert not any(token in identity.name.lower().split() for identity in generated for token in forbidden_defaults)


def test_gendered_avatar_selection_excludes_opposite_gender_portrait(tmp_path, monkeypatch):
    avatars = []
    for name in ("avatar-01-woman-realistic.png", "avatar-02-man-realistic.png", "avatar-03-cat-meme.png"):
        path = tmp_path / name
        path.write_bytes(b"avatar")
        avatars.append(path)
    monkeypatch.setattr("core.employee_identity.random.random", lambda: 1.0)
    selected = []
    monkeypatch.setattr("core.employee_identity.random.choice", lambda values: values[len(selected) % len(values)])
    for _ in avatars:
        selected.append(_pick_avatar(tmp_path, "female"))

    assert str(avatars[1]) not in selected
    assert set(selected) <= {str(avatars[0]), str(avatars[2])}


def test_generated_human_profile_never_uses_opposite_gender_portrait(tmp_path, monkeypatch):
    woman = tmp_path / "avatar-01-woman-realistic.png"
    man = tmp_path / "avatar-02-man-realistic.png"
    cat = tmp_path / "avatar-03-cat-meme.png"
    for path in (woman, man, cat):
        path.write_bytes(b"avatar")
    monkeypatch.setattr("core.employee_identity.random.random", lambda: 0.1)

    assert _pick_avatar(tmp_path, "female") == str(woman)
    assert _pick_avatar(tmp_path, "male") == str(man)


def test_500_generated_employees_use_the_broad_avatar_and_personality_catalog():
    import random

    avatar_dir = Path(__file__).resolve().parents[1] / "data" / "avatars"
    state = random.getstate()
    try:
        random.seed(2050)
        generated = [generate_identity("ru", avatar_dir=avatar_dir) for _ in range(500)]
    finally:
        random.setstate(state)

    unique_avatars = {identity.avatar_path for identity in generated}
    unique_profiles = {
        tuple(sorted(identity.communication_profile.items()))
        for identity in generated
    }
    # Gendered portrait mismatches are excluded; the neutral catalog remains broad.
    assert len(unique_avatars) >= 75
    assert len(unique_profiles) >= 400
