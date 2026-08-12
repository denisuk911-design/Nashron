from pathlib import Path

from core.avatar_catalog import list_avatar_files
from core.employee_identity import generate_identity


def test_generated_identity_has_editable_profile_fields_and_avatar(tmp_path):
    (tmp_path / "avatar-01-woman-realistic.png").write_bytes(b"avatar")

    identity = generate_identity("ru", "female", tmp_path)

    assert identity.name
    assert identity.gender == "female"
    assert identity.biography
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
