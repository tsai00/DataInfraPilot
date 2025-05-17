from src.core.providers.base_provider import BaseProvider
from src.core.providers.hetzner.hetzner_provider import HetznerProvider, HetznerConfig


class ProviderFactory:
    @staticmethod
    def get_provider(provider_type: str, provider_config: dict) -> BaseProvider:
        if provider_type.lower() == "hetzner":
            return HetznerProvider(HetznerConfig(**provider_config))

        raise ValueError(f"Unknown provider: {provider_type}")