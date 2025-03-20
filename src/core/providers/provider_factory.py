from src.core.providers.base_provider import BaseProvider
from src.core.providers.hetzner.hetzner_provider import HetznerProvider


class ProviderFactory:
    @staticmethod
    def get_provider(provider_type: str) -> BaseProvider:
        if provider_type.lower() == "hetzner":
            return HetznerProvider()

        raise ValueError(f"Unknown provider: {provider_type}")