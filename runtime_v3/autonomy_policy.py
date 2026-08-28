from __future__ import annotations

from .models import Action, ActionType


class AutonomyPolicy:
    """Local workspace work is autonomous; external and commercial actions are not."""

    EXTERNAL_ACTIONS = {ActionType.MCP_CALL, ActionType.BROWSER_CALL}
    RISK_TOKENS = ("publish", "publication", "deploy", "purchase", "payment", "money", "transfer", "оплат", "куп", "публикац")

    @classmethod
    def requires_owner_approval(cls, action: Action) -> bool:
        if action.action_type in cls.EXTERNAL_ACTIONS:
            return True
        payload = " ".join(str(value) for value in action.payload.values()).lower()
        return any(token in payload for token in cls.RISK_TOKENS)
