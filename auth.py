"""
BetOdds Web - Autenticazione e gestione utenti.
"""

from functools import wraps
from flask import session, redirect, url_for

from web_storage import get_user_by_id, get_user_by_username


def login_required(f):
    """Decorator: richiede login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator: richiede login e ruolo admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        user = get_user_by_id(session["user_id"])
        if not user or user.get("ruolo") != "admin":
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    """Restituisce l'utente correntemente loggato o None."""
    uid = session.get("user_id")
    if not uid:
        return None
    return get_user_by_id(uid)


def is_admin():
    """True se l'utente corrente è admin."""
    user = get_current_user()
    return user and user.get("ruolo") == "admin"
