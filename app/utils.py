"""Malé pomocné funkcie bez závislostí na zvyšku aplikácie."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naivný UTC datetime — náhrada za deprecated ``datetime.utcnow()``.

    Vracia naivný datetime (bez ``tzinfo``), aby zostala zhoda s existujúcimi
    ``DateTime`` stĺpcami a porovnaniami v kóde (žiadne miešanie aware/naive).
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
