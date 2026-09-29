"""Motor de Sinais Jurídicos (JUR-04).

Detecta EVIDÊNCIAS processuais (sinais) a partir de dados já normalizados
(movimentos, assuntos, classes). Não emite parecer nem decisão jurídica; a
correlação com o imóvel e o risco jurídico ficam no módulo Jurídico do Radar.
"""

from .rules import SignalRule, load_signal_rules, default_signal_rules
from .engine import SignalEngine

__all__ = ["SignalRule", "load_signal_rules", "default_signal_rules", "SignalEngine"]
