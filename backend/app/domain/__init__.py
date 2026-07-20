from __future__ import annotations

from .config import DomainConfig
from .real_estate import REAL_ESTATE_DOMAIN


def get_default_domain_config() -> DomainConfig:
    return REAL_ESTATE_DOMAIN


__all__ = ["DomainConfig", "REAL_ESTATE_DOMAIN", "get_default_domain_config"]

