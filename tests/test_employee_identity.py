from pathlib import Path

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
