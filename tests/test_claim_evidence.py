from core.claim_evidence import ClaimEvidenceValidator, ClaimValidationResult


def test_completion_claim_without_evidence_is_unsupported():
    result = ClaimEvidenceValidator().validate("Проверил файл, ошибок нет.", None)

    assert result.result == ClaimValidationResult.CLAIM_UNSUPPORTED
    assert result.blocks_skill_update
    assert "не подтверждено" in result.warning


def test_file_read_claim_with_evidence_is_supported():
    result = ClaimEvidenceValidator().validate(
        "Прочитал файл и нашел проблему.",
        {"files_read": ["docs/a.md"], "checks": ["source evidence"]},
    )

    assert result.result == ClaimValidationResult.CLAIM_SUPPORTED
    assert not result.blocks_skill_update


def test_skill_mastered_claim_is_never_accepted_from_chat_text_only():
    result = ClaimEvidenceValidator().validate("Навык освоен, обучение завершено.", {"checks": ["self report"]})

    assert result.result == ClaimValidationResult.CLAIM_UNSUPPORTED
    assert result.blocks_skill_update
