from __future__ import annotations

from dataclasses import dataclass

from .provider_service import ProviderHealthService, ProviderRegistry


@dataclass(frozen=True)
class ProviderHubEntry:
    provider_id: str
    display_name: str
    status: str
    ready: bool
    capabilities: tuple[str, ...]
    detail: str = ""


class ProviderHubService:
    """Read-only product-facing view over provider registry and health."""

    def __init__(self, registry: ProviderRegistry, health: ProviderHealthService, developer_mode: bool = False) -> None:
        self.registry = registry
        self.health = health
        self.developer_mode = developer_mode

    def entries(self, refresh: bool = False) -> list[ProviderHubEntry]:
        entries: list[ProviderHubEntry] = []
        for profile in self.registry.profiles():
            health = self.health.check_provider(profile.provider_id) if refresh else self.health.latest_health(profile.provider_id)
            status = self._product_status(health)
            entries.append(ProviderHubEntry(
                provider_id=profile.provider_id,
                display_name=profile.display_name,
                status=status,
                ready=status == "Ready",
                capabilities=tuple(sorted(str(item) for item in profile.capability_matrix)),
                detail=health.diagnostic if health is not None and self.developer_mode else "",
            ))
        return entries

    @staticmethod
    def _product_status(health) -> str:
        if health is None:
            return "Offline"
        if health.health_status == "BUSY":
            return "Busy"
        if health.installation_status != "INSTALLED":
            return "Offline"
        if health.authentication_status not in {"AUTHENTICATED", "NOT_REQUIRED"}:
            return "Login needed"
        if health.health_status in {"READY", "DEGRADED"}:
            return "Ready"
        return "Error"
