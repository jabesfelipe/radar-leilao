"""Providers da Judicial API.

- JUR-01: interface base ``JudicialProvider``.
- JUR-02: implementação concreta ``DataJudProvider``.
"""

from .base import JudicialProvider, ProviderCapabilities
from .datajud import PROVIDER_CODE, DataJudProvider

__all__ = ["JudicialProvider", "ProviderCapabilities", "DataJudProvider", "PROVIDER_CODE"]
