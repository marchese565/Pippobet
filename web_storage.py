"""
BetOdds Web - Storage per partite e scommesse del sito.
Usa JSON separato dalla versione CLI.
Multi-utente: partite, scommesse, schedine e bankroll sono per user_id.
"""

import json
from pathlib import Path

DIR_WEB = Path(__file__).parent
FILE_USERS = DIR_WEB / "users.json"
FILE_PARTITE = DIR_WEB / "partite_web.json"
FILE_SCOMMESSE = DIR_WEB / "scommesse_web.json"
FILE_SCOMMESSE_VIRTUALI = DIR_WEB / "scommesse_virtuali.json"
FILE_SCHEDINE = DIR_WEB / "schedine_virtuali.json"
FILE_BANKROLL = DIR_WEB / "bankroll.json"


def _carica_json(path: Path, default: list | dict) -> list | dict:
    if not path.exists():
        return default if isinstance(default, list) else default.copy()
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default if isinstance(default, list) else default.copy()


def _salva_json(path: Path, data: list | dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# =============================================================================
# UTENTI
# =============================================================================


def carica_utenti() -> list[dict]:
    """Carica la lista degli utenti."""
    data = _carica_json(FILE_USERS, [])
    return data if isinstance(data, list) else []


def salva_utenti(utenti: list[dict]) -> None:
    """Salva la lista degli utenti."""
    _salva_json(FILE_USERS, utenti)


def get_user_by_id(user_id: int) -> dict | None:
    """Restituisce un utente per id."""
    for u in carica_utenti():
        if u.get("id") == user_id:
            return u
    return None


def get_user_by_username(username: str) -> dict | None:
    """Restituisce un utente per username (case-insensitive)."""
    un = (username or "").strip().lower()
    if not un:
        return None
    for u in carica_utenti():
        if (u.get("username") or "").lower() == un:
            return u
    return None


def crea_utente(username: str, password_hash: str, ruolo: str = "user") -> dict:
    """Crea un nuovo utente. Restituisce l'utente con id."""
    utenti = carica_utenti()
    if get_user_by_username(username):
        raise ValueError("Username già esistente")
    new_id = max((u.get("id", 0) for u in utenti), default=0) + 1
    user = {"id": new_id, "username": username.strip(), "password_hash": password_hash, "ruolo": ruolo}
    utenti.append(user)
    salva_utenti(utenti)
    return user


def init_admin_se_necessario() -> None:
    """Crea utente admin (admin/admin) se non esistono utenti."""
    if carica_utenti():
        return
    from werkzeug.security import generate_password_hash
    crea_utente("admin", generate_password_hash("admin"), "admin")


def aggiorna_ruolo_utente(user_id: int, ruolo: str) -> bool:
    """Aggiorna il ruolo di un utente. Restituisce True se ok."""
    utenti = carica_utenti()
    for i, u in enumerate(utenti):
        if u.get("id") == user_id:
            utenti[i] = {**u, "ruolo": ruolo}
            salva_utenti(utenti)
            return True
    return False


# =============================================================================
# PARTITE (per user_id)
# =============================================================================


def carica_partite(user_id: int | None = None) -> list[dict]:
    """Carica le partite. Se user_id, solo quelle dell'utente. None = tutte (admin)."""
    partite = _carica_json(FILE_PARTITE, [])
    partite = partite if isinstance(partite, list) else []
    if user_id is not None:
        partite = [p for p in partite if p.get("user_id", 1) == user_id]
    return partite


def salva_partite(partite: list[dict]) -> None:
    """Salva la lista delle partite."""
    _salva_json(FILE_PARTITE, partite)


def carica_scommesse(user_id: int | None = None) -> list[dict]:
    """Carica le scommesse. Se user_id, solo quelle dell'utente. None = tutte."""
    scommesse = _carica_json(FILE_SCOMMESSE, [])
    scommesse = scommesse if isinstance(scommesse, list) else []
    if user_id is not None:
        scommesse = [s for s in scommesse if s.get("user_id", 1) == user_id]
    return scommesse


def salva_scommesse(scommesse: list[dict]) -> None:
    """Salva la lista delle scommesse."""
    _salva_json(FILE_SCOMMESSE, scommesse)


def aggiungi_partita(partita: dict, user_id: int | None = None) -> dict:
    """Aggiunge una partita e restituisce la partita con id."""
    partite = _carica_json(FILE_PARTITE, [])
    partite = partite if isinstance(partite, list) else []
    new_id = max((p.get("id", 0) for p in partite), default=0) + 1
    partita["id"] = new_id
    partita["esito"] = None
    partita["user_id"] = user_id or partita.get("user_id", 1)
    partite.append(partita)
    salva_partite(partite)
    return partita


def get_partita(partita_id: int) -> dict | None:
    """Restituisce una partita per id."""
    for p in carica_partite():
        if p.get("id") == partita_id:
            return p
    return None


def aggiorna_partita(partita_id: int, **kwargs) -> bool:
    """Aggiorna una partita esistente."""
    partite = carica_partite()
    for i, p in enumerate(partite):
        if p.get("id") == partita_id:
            partite[i] = {**p, **kwargs}
            salva_partite(partite)
            return True
    return False


def aggiungi_scommessa(scommessa: dict, user_id: int | None = None) -> dict:
    """Aggiunge una scommessa e restituisce la scommessa con id."""
    scommesse = _carica_json(FILE_SCOMMESSE, [])
    scommesse = scommesse if isinstance(scommesse, list) else []
    new_id = max((s.get("id", 0) for s in scommesse), default=0) + 1
    scommessa["id"] = new_id
    scommessa["user_id"] = user_id or scommessa.get("user_id", 1)
    scommesse.append(scommessa)
    salva_scommesse(scommesse)
    return scommessa


def scommesse_per_partita(partita_id: int, user_id: int | None = None) -> list[dict]:
    """Restituisce le scommesse associate a una partita (filtrate per user se specificato)."""
    tutte = carica_scommesse(user_id)
    return [s for s in tutte if s.get("partita_id") == partita_id]


def rimuovi_scommessa(scommessa_id: int) -> dict | None:
    """Rimuove una scommessa per id. Restituisce la scommessa rimossa o None."""
    tutte = carica_scommesse()
    for i, s in enumerate(tutte):
        if s.get("id") == scommessa_id:
            rimossa = tutte.pop(i)
            salva_scommesse(tutte)
            return rimossa
    return None


# =============================================================================
# SCOMMESSE VIRTUALI (campionato)
# =============================================================================


def carica_scommesse_virtuali() -> list[dict]:
    """Carica le scommesse virtuali sul campionato."""
    data = _carica_json(FILE_SCOMMESSE_VIRTUALI, [])
    return data if isinstance(data, list) else []


def salva_scommesse_virtuali(scommesse: list[dict]) -> None:
    """Salva le scommesse virtuali."""
    _salva_json(FILE_SCOMMESSE_VIRTUALI, scommesse)


def aggiungi_scommessa_virtuale(scommessa: dict) -> dict:
    """Aggiunge una scommessa virtuale."""
    tutte = carica_scommesse_virtuali()
    new_id = max((s.get("id", 0) for s in tutte), default=0) + 1
    scommessa["id"] = new_id
    scommessa.setdefault("esito_partita", None)
    scommessa.setdefault("vinto", None)
    scommessa.setdefault("vincita", None)
    tutte.append(scommessa)
    salva_scommesse_virtuali(tutte)
    return scommessa


def scommesse_virtuali_per_match(giornata: int, ic: int, it: int) -> list[dict]:
    """Restituisce le scommesse virtuali per una partita del campionato."""
    return [
        s for s in carica_scommesse_virtuali()
        if s.get("giornata") == giornata and s.get("ic") == ic and s.get("it") == it
    ]


# =============================================================================
# SCHEDINE VIRTUALI
# =============================================================================


def carica_schedine(user_id: int | None = None) -> list[dict]:
    """Carica le schedine. Se user_id, solo quelle dell'utente. None = tutte."""
    data = _carica_json(FILE_SCHEDINE, [])
    tutte = data if isinstance(data, list) else []
    if tutte:
        _assicura_id_schedine(tutte)
    if user_id is not None:
        tutte = [s for s in tutte if s.get("user_id", 1) == user_id]
    return tutte


def salva_schedine(schedine: list[dict]) -> None:
    """Salva le schedine virtuali."""
    _salva_json(FILE_SCHEDINE, schedine)


BANKROLL_INIZIALE = 1000.0


def carica_bankroll(user_id: int | None = None) -> float:
    """Carica il bankroll. user_id obbligatorio per multi-utente. Legacy: senza user_id usa 'bankroll' o user 1."""
    data = _carica_json(FILE_BANKROLL, {"bankroll": BANKROLL_INIZIALE})
    if not isinstance(data, dict):
        return BANKROLL_INIZIALE
    if user_id is not None:
        key = str(user_id)
        if key in data:
            return float(data[key])
        return BANKROLL_INIZIALE
    if "bankroll" in data:
        return float(data["bankroll"])
    return float(data.get("1", BANKROLL_INIZIALE))


def salva_bankroll(valore: float, user_id: int | None = None) -> None:
    """Salva il bankroll per l'utente. Legacy: senza user_id usa 'bankroll'."""
    data = _carica_json(FILE_BANKROLL, {})
    if not isinstance(data, dict):
        data = {}
    if user_id is not None:
        data[str(user_id)] = valore
    else:
        data["bankroll"] = valore
    _salva_json(FILE_BANKROLL, data)


def aggiungi_schedina(schedina: dict, user_id: int | None = None) -> dict:
    """Aggiunge una schedina."""
    tutte = _carica_json(FILE_SCHEDINE, [])
    tutte = tutte if isinstance(tutte, list) else []
    new_id = max((s.get("id", 0) for s in tutte), default=0) + 1
    schedina["id"] = new_id
    schedina["user_id"] = user_id or schedina.get("user_id", 1)
    schedina.setdefault("vinto", None)
    schedina.setdefault("vincita", None)
    schedina.setdefault("eventi_sbagliati", None)
    tutte.append(schedina)
    salva_schedine(tutte)
    return schedina


def _assicura_id_schedine(tutte: list[dict]) -> None:
    """Assegna un id a schedine che non lo hanno."""
    max_id = max((s.get("id", 0) for s in tutte), default=0)
    modified = False
    for s in tutte:
        if "id" not in s or s["id"] is None:
            max_id += 1
            s["id"] = max_id
            modified = True
    if modified:
        salva_schedine(tutte)


def rimuovi_schedina(schedina_id: int) -> tuple[dict | None, bool]:
    """Rimuove una schedina per id. Restituisce (schedina_rimossa, era_in_attesa)."""
    tutte = carica_schedine()
    _assicura_id_schedine(tutte)
    for i, s in enumerate(tutte):
        if s.get("id") == schedina_id:
            era_in_attesa = s.get("vinto") is None
            tutte.pop(i)
            salva_schedine(tutte)
            return s, era_in_attesa
    return None, False


def rimuovi_evento_schedina(schedina_id: int, ic: int, it: int) -> tuple[dict | None, float]:
    """
    Rimuove un singolo evento (ic, it) da una schedina in attesa.
    Ricalcola quota_combinata e vincita_potenziale.
    Se non rimangono eventi, elimina la schedina.
    Restituisce (schedina_modificata, puntata_da_rimborsare). puntata_da_rimborsare > 0 se eliminata.
    """
    tutte = carica_schedine()
    _assicura_id_schedine(tutte)
    for s in tutte:
        if s.get("id") != schedina_id:
            continue
        if s.get("vinto") is not None:
            return None, 0.0
        selezioni = s.get("selezioni", [])
        nuove = [sel for sel in selezioni if sel.get("ic") != ic or sel.get("it") != it]
        if len(nuove) == len(selezioni):
            return None, 0.0
        if len(nuove) == 0:
            puntata = s.get("puntata", 0)
            tutte.remove(s)
            salva_schedine(tutte)
            return None, puntata
        quota_tot = 1.0
        for sel in nuove:
            quota_tot *= sel.get("quota", 1)
        s["selezioni"] = nuove
        s["quota_combinata"] = round(quota_tot, 2)
        s["vincita_potenziale"] = round(s.get("puntata", 0) * quota_tot, 2)
        salva_schedine(tutte)
        return s, 0.0
    return None, 0.0
