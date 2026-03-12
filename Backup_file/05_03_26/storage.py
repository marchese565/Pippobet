"""
BetOdds Simulator - Modulo storage.
Gestisce la persistenza dei dati (cronologia partite, session).
"""

import csv
import json
from datetime import datetime
from pathlib import Path

FILE_CRONOLOGIA = Path(__file__).parent / "cronologia.json"
FILE_SESSION = Path(__file__).parent / "session.json"
FILE_CRONOLOGIA_CSV = Path(__file__).parent / "cronologia.csv"


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


# =============================================================================
# SESSION (calcoli quote e simulazioni)
# =============================================================================


def carica_sessione() -> list[dict]:
    """Carica la sessione (calcoli e simulazioni) dal file."""
    if not FILE_SESSION.exists():
        return []
    try:
        with open(FILE_SESSION, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def salva_sessione(sessione: list[dict]) -> None:
    """Salva la sessione su file."""
    with open(FILE_SESSION, "w", encoding="utf-8") as f:
        json.dump(sessione, f, indent=2, ensure_ascii=False)


def aggiungi_evento_sessione(tipo: str, dati: dict) -> None:
    """Aggiunge un evento alla sessione e salva."""
    evento = {
        "tipo": tipo,
        "timestamp": datetime.now().isoformat(),
        **dati,
    }
    sessione = carica_sessione()
    sessione.append(evento)
    salva_sessione(sessione)


def elimina_cronologia() -> None:
    """Elimina cronologia partite e sessione (calcoli e simulazioni)."""
    salva_cronologia([])
    salva_sessione([])


def _riga_evento_per_csv(ev: dict) -> dict[str, str]:
    """Converte un evento della sessione in una riga per CSV (Data, Ora, Evento, Quote, Risultato)."""
    ts = ev.get("timestamp", "")
    try:
        parti = ts.split("T")
        data = parti[0] if parti else ts
        ora = parti[1][:8] if len(parti) > 1 and len(parti[1]) >= 8 else ""
    except (IndexError, AttributeError):
        data, ora = ts, ""
    tipo = ev.get("tipo", "?")

    if tipo == "calcolo_quote":
        evento_nome = "Calcolo quote"
        quote = ev.get("quote_book", ev.get("quote_giuste", []))
        quote_str = ", ".join(f"{q:.2f}" for q in quote) if quote else ""
        risultato = f"Quote book: {quote_str}"
    elif tipo == "simula_scommessa":
        evento_nome = ev.get("nome", "Simula scommessa")
        quote = ev.get("quote_book", [])
        quote_str = ", ".join(f"{q:.2f}" for q in quote) if quote else ""
        risultato = f"Quote: {quote_str}"
    elif tipo == "simulazione":
        evento_nome = "Simulazione scommesse"
        bankroll_f = ev.get("bankroll_finale", 0)
        vittorie = ev.get("vittorie", 0)
        totali = ev.get("totali", 0)
        variaz = ev.get("variazione_pct", 0)
        quote_str = f"{ev.get('quota_min', 0):.2f}-{ev.get('quota_max', 0):.2f}"
        risultato = f"Bankroll finale: {bankroll_f:,.0f} | Vittorie: {vittorie}/{totali} | Variaz: {variaz:+.1f}%"
    else:
        evento_nome = tipo
        quote_str = ""
        risultato = ""

    return {"Data": data, "Ora": ora, "Evento": evento_nome, "Quote": quote_str, "Risultato": risultato}


def esporta_cronologia_csv(path: Path | None = None) -> Path:
    """
    Esporta la cronologia (sessione) in un file CSV leggibile con Excel.
    Usa separatore ';' e UTF-8 con BOM per compatibilità Excel.
    Restituisce il path del file scritto.
    """
    path = path or FILE_CRONOLOGIA_CSV
    sessione = carica_sessione()
    colonne = ["Data", "Ora", "Evento", "Quote", "Risultato"]
    righe = [_riga_evento_per_csv(ev) for ev in reversed(sessione)]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=colonne, delimiter=";")
        writer.writeheader()
        writer.writerows(righe)
    return path
