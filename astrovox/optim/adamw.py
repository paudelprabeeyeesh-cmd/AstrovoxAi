"""Re-export of AdamW alongside Adam.

``AdamW`` is defined in :mod:`astrovox.optim.adam` because it is Adam with
``decoupled_weight_decay`` forced on. This module mirrors the conventional
``from astrovox.optim.adamw import AdamW`` import path.
"""

from astrovox.optim.adam import Adam, AdamW

__all__ = ["Adam", "AdamW"]
