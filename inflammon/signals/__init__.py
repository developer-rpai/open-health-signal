"""Signal statistics: disproportionality and weekly spike detection."""

from inflammon.signals.disproportionality import Disproportionality, disproportionality
from inflammon.signals.trends import SpikeResult, detect_latest_spike, trailing_spikes

__all__ = [
    "Disproportionality",
    "SpikeResult",
    "detect_latest_spike",
    "disproportionality",
    "trailing_spikes",
]
