"""koine-suno: respell Koine Greek so Suno sings it correctly.

Typical use::

    >>> from koine_suno import to_suno, to_ipa
    >>> to_ipa("λόγος")
    'ˈlo.ɡos'
    >>> to_suno("λόγος")
    'LOH-goss'
"""

from .ipa import to_ipa, transcribe
from .suno import SunoOptions, breakdown, to_suno

__all__ = ["SunoOptions", "breakdown", "to_ipa", "to_suno", "transcribe"]
__version__ = "0.1.0"
