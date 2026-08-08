"""Text normalization helpers shared across search and sort code."""
from __future__ import annotations

import unicodedata


def normalize_for_match(value) -> str:
    """Return a lowercase, diacritic-free version of `value` for matching.

    Strips accents (NFKD normalization, dropping combining marks) and
    casefolds, so "Álvaro" and "Alvaro" compare equal. Shared by
    TableSortMixin._normalize_for_sort (header-click sorting) and
    MembersMenuService (DB text search) so both stay accent-insensitive
    the same way.
    """
    if value is None:
        return ""
    try:
        s = str(value)
        nkfd = unicodedata.normalize("NFKD", s)
        stripped = "".join(ch for ch in nkfd if not unicodedata.combining(ch))
        return stripped.casefold().strip()
    except Exception:
        return str(value).casefold() if value is not None else ""
