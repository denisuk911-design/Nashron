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


class ProviderHubService:
    """Read-only product-facing view over provider registry and health."""

    def __init__(self, registry: ProviderRegistry, health: ProviderHealthService) -> None:
        self.registry = registry
        self.health = health

    def entries(self, refresh: bool = False) -> list[ProviderHubEntry]:
        entries: list[ProviderHubEntry] = []
        for profile in self.registry.profiles():
            health = self.health.check_provider(profile.provider_id) if refresh else self.health.latest_health(profile.provider_id)
            status = health.health_status if health is not None else "NOT_CHECKED"
            entries.append(ProviderHubEntry(
                provider_id=profile.provider_id,
                display_name=profile.display_name,
                status=status,
                ready=status in {"READY", "DEGRADED"},
                capabilities=tuple(sorted(str(item) for item in profile.capability_matrix)),
            ))
        return entries
