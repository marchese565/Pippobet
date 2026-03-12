"""
BetOdds Simulator - Modulo storage.
Gestisce la persistenza dei dati (cronologia partite).
"""

import json
from pathlib import Path

FILE_CRONOLOGIA = Path(__file__).parent / "cronologia.json"


def carica_cronologia() -> list[dict]:
    """Carica la cronologia partite dal file."""
    if not FILE_CRONOLOGIA.exists():
        return []
    try:
        with open(FILE_CRONOLOGIA, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def salva_cronologia(cronologia: list[dict]) -> None:
    """Salva la cronologia partite su file."""
    with open(FILE_CRONOLOGIA, "w", encoding="utf-8") as f:
        json.dump(cronologia, f, indent=2, ensure_ascii=False)


def aggiungi_partita(cronologia: list[dict], partita: dict) -> None:
    """Aggiunge una partita alla cronologia e salva."""
    cronologia.append(partita)
    salva_cronologia(cronologia)
