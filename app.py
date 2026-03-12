"""
BetOdds Web - Sito scommesse basato sulla logica odds.py e campionato.
Avvio: python app.py
Multi-utente con ruoli Admin e Utente.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash

from auth import login_required, admin_required, get_current_user, is_admin
from odds import (
    probabilita_valide,
    quote_bookmaker_da_probabilita,
    quote_doppie_da_probabilita,
    quote_over_under,
    simula_esito,
    simula_gol,
    scommessa_vincente,
    scommessa_ou_vincente,
    calcola_vincita,
)
from campionato import quote_partita as campionato_quote_partita, gioca_giornata, inizializza_campionato
from storage import carica_campionato, carica_squadre

from web_storage import (
    carica_partite,
    aggiungi_partita,
    get_partita,
    aggiorna_partita,
    aggiungi_scommessa,
    scommesse_per_partita,
    carica_scommesse,
    rimuovi_scommessa,
    carica_schedine,
    salva_schedine,
    aggiungi_schedina,
    rimuovi_schedina,
    rimuovi_evento_schedina,
    carica_bankroll,
    salva_bankroll,
    carica_utenti,
    get_user_by_username,
    crea_utente,
    init_admin_se_necessario,
    aggiorna_ruolo_utente,
)

TIPI_SCHEDINA = ("1", "X", "2", "1X", "X2", "12",
                 "Over1.5", "Under1.5", "Over2.5", "Under2.5", "Over3.5", "Under3.5")

# Sigle ufficiali Serie A (fonte legaseriea.it)
SIGLE_SQUADRE = {
    "inter": "INT", "juventus": "JUV", "milan": "MIL", "roma": "ROM",
    "atalanta": "ATA", "bologna": "BOL", "cagliari": "CAG", "como": "COM",
    "cremonese": "CRE", "fiorentina": "FIO", "genoa": "GEN",
    "hellas verona": "VER", "lazio": "LAZ", "lecce": "LEC", "napoli": "NAP",
    "parma": "PAR", "pisa": "PIS", "sassuolo": "SAS", "torino": "TOR",
    "udinese": "UDI",
}


def _sigla_squadra(nome: str) -> str:
    """Restituisce la sigla (3 lettere) per il nome squadra."""
    return SIGLE_SQUADRE.get(nome.lower().strip(), nome[:3].upper() if nome else "???")


def _calendario_risultati(campionato: dict | None, partite_giornata: list | None = None) -> list[dict]:
    """Raggruppa risultati per giornata con sigle e punteggio. Incl. giornata corrente se non ancora giocata."""
    if not campionato:
        return []
    squadre = campionato.get("squadre", [])
    risultati = campionato.get("risultati", [])
    calendario = campionato.get("calendario", [])
    gc = campionato.get("giornata_corrente", 0)
    by_g = {}
    for r in risultati:
        g = r.get("giornata", 0)
        if g not in by_g:
            by_g[g] = []
        ic, it = r.get("casa", 0), r.get("trasferta", 0)
        nome_casa = squadre[ic]["nome"] if ic < len(squadre) else "?"
        nome_trasf = squadre[it]["nome"] if it < len(squadre) else "?"
        gol_c = r.get("gol_casa")
        gol_t = r.get("gol_trasferta")
        if gol_c is None or gol_t is None:
            esito = r.get("esito", 1)
            if esito == 0:
                gol_c, gol_t = 1, 0
            elif esito == 2:
                gol_c, gol_t = 0, 1
            else:
                gol_c, gol_t = 1, 1
        by_g[g].append({
            "sigla_casa": _sigla_squadra(nome_casa),
            "sigla_trasf": _sigla_squadra(nome_trasf),
            "gol_casa": gol_c,
            "gol_trasf": gol_t,
        })
    # Aggiungi giornata corrente se non ancora giocata (così il calendario è sempre visibile)
    if partite_giornata and gc < len(calendario):
        g_curr = gc + 1
        if g_curr not in by_g:
            by_g[g_curr] = []
            for p in partite_giornata:
                by_g[g_curr].append({
                    "sigla_casa": _sigla_squadra(p.get("casa", "?")),
                    "sigla_trasf": _sigla_squadra(p.get("trasferta", "?")),
                    "gol_casa": None,
                    "gol_trasf": None,
                })
    return [{"giornata": g, "partite": partite} for g, partite in sorted(by_g.items())]


app = Flask(__name__)
app.secret_key = "betodds-web-key-change-in-production"
MARGINE_DEFAULT = 0.05

# Crea admin (admin/admin) se non esistono utenti
init_admin_se_necessario()


# =============================================================================
# AUTH - Login, Logout, Registrati
# =============================================================================


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login utente."""
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("index"))
        return render_template("login.html")
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    user = get_user_by_username(username)
    if not user or not check_password_hash(user.get("password_hash", ""), password):
        flash("Username o password errati.", "error")
        return redirect(url_for("login"))
    session["user_id"] = user["id"]
    flash(f"Bentornato, {user['username']}!")
    return redirect(request.args.get("next") or url_for("index"))


@app.route("/logout")
def logout():
    """Logout."""
    session.pop("user_id", None)
    flash("Sei uscito.")
    return redirect(url_for("login"))


@app.route("/registrati", methods=["GET", "POST"])
def registrati():
    """Registrazione nuovo utente."""
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("index"))
        return render_template("registrati.html")
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    password2 = request.form.get("password2", "")
    if not username or len(username) < 2:
        flash("Username deve avere almeno 2 caratteri.", "error")
        return redirect(url_for("registrati"))
    if len(password) < 4:
        flash("La password deve avere almeno 4 caratteri.", "error")
        return redirect(url_for("registrati"))
    if password != password2:
        flash("Le password non coincidono.", "error")
        return redirect(url_for("registrati"))
    try:
        user = crea_utente(username, generate_password_hash(password), "user")
        session["user_id"] = user["id"]
        flash(f"Account creato! Bentornato, {username}.")
        return redirect(url_for("index"))
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("registrati"))


# =============================================================================
# ROUTES PUBBLICHE (redirect a login se non autenticato)
# =============================================================================


def _user_id():
    """ID utente corrente (1 se non loggato, per retrocompat)."""
    return session.get("user_id", 1)


@app.route("/")
@login_required
def index():
    """Homepage: lista partite."""
    uid = _user_id()
    partite = carica_partite(None) if is_admin() else carica_partite(uid)
    for p in partite:
        p["quote"] = _quote_partita(p)
        p["esito_label"] = {0: "1", 1: "X", 2: "2"}.get(p.get("esito"), None)
    return render_template("index.html", partite=partite)


@app.route("/bankroll/ricarica", methods=["GET", "POST"])
@login_required
def bankroll_ricarica():
    """Ricarica il bankroll."""
    uid = _user_id()
    if request.method == "GET":
        return render_template("bankroll_ricarica.html")
    try:
        importo = float(request.form.get("importo", 0))
    except ValueError:
        importo = 0
    if importo <= 0:
        flash("Inserisci un importo valido.", "error")
        return redirect(url_for("bankroll_ricarica"))
    bankroll = carica_bankroll(uid)
    salva_bankroll(bankroll + importo, uid)
    flash(f"Bankroll ricaricato di €{importo:,.2f}")
    return redirect(request.referrer or url_for("virtuali"))


@app.context_processor
def inject_template_vars():
    """Inietta variabili in tutti i template."""
    user = get_current_user()
    bankroll = carica_bankroll(user["id"]) if user else 1000
    return {
        "bankroll": bankroll,
        "current_user": user,
        "is_admin": is_admin(),
    }


def _quote_partita(partita: dict) -> dict:
    """Calcola quote 1,X,2, doppie e O/U per una partita. Usa quote_custom se presenti."""
    prob = partita.get("probabilita", [])
    margine = partita.get("margine", MARGINE_DEFAULT)
    custom = partita.get("quote_custom", {})
    base = {"1": 0, "X": 0, "2": 0, "1X": 0, "X2": 0, "12": 0,
            "Over1.5": 0, "Over2.5": 0, "Over3.5": 0, "Under1.5": 0, "Under2.5": 0, "Under3.5": 0}
    if not probabilita_valide(prob) or len(prob) != 3:
        return {**base, **custom}
    q123 = quote_bookmaker_da_probabilita(prob, margine)
    q_doppie = quote_doppie_da_probabilita(prob, margine)
    out = {
        "1": round(q123[0], 2),
        "X": round(q123[1], 2),
        "2": round(q123[2], 2),
        "1X": custom["1X"] if "1X" in custom else round(q_doppie["1X"], 2),
        "X2": custom["X2"] if "X2" in custom else round(q_doppie["X2"], 2),
        "12": custom["12"] if "12" in custom else round(q_doppie["12"], 2),
    }
    q_ou_default = quote_over_under(50, 50, margine)
    for k in ["Over1.5", "Over2.5", "Over3.5", "Under1.5", "Under2.5", "Under3.5"]:
        out[k] = custom[k] if k in custom else round(q_ou_default.get(k, 1.0), 2)
    return out


@app.route("/partita/nuova", methods=["GET", "POST"])
@login_required
def nuova_partita():
    """Crea nuova partita con nome e probabilità."""
    if request.method == "GET":
        return render_template("nuova_partita.html")
    nome = request.form.get("nome", "").strip()
    if not nome:
        flash("Inserisci il nome della partita.", "error")
        return redirect(url_for("nuova_partita"))
    try:
        p1 = float(request.form.get("prob1", 0))
        px = float(request.form.get("probX", 0))
        p2 = float(request.form.get("prob2", 0))
        margine = float(request.form.get("margine", 5))
        if margine > 1:
            margine /= 100
    except ValueError:
        flash("Probabilità e margine devono essere numeri.", "error")
        return redirect(url_for("nuova_partita"))
    prob = [p1, px, p2]
    if not probabilita_valide(prob):
        flash(f"Le probabilità devono sommare 1.0 (somma attuale: {sum(prob):.3f})", "error")
        return redirect(url_for("nuova_partita"))
    quote_custom = {}
    for key, form_key in [
        ("1X", "q_1X"), ("X2", "q_X2"), ("12", "q_12"),
        ("Over1.5", "q_Over15"), ("Over2.5", "q_Over25"), ("Over3.5", "q_Over35"),
        ("Under1.5", "q_Under15"), ("Under2.5", "q_Under25"), ("Under3.5", "q_Under35"),
    ]:
        v = request.form.get(form_key, "").strip()
        if v:
            try:
                quote_custom[key] = round(float(v), 2)
            except ValueError:
                pass
    partita = aggiungi_partita({
        "nome": nome,
        "probabilita": prob,
        "margine": margine,
        **({"quote_custom": quote_custom} if quote_custom else {}),
    }, user_id=_user_id())
    flash(f"Partita '{nome}' creata.")
    return redirect(url_for("partita", partita_id=partita["id"]))


@app.route("/partita/<int:partita_id>")
@login_required
def partita(partita_id):
    """Dettaglio partita con quote e form scommessa."""
    uid = _user_id()
    p = get_partita(partita_id)
    if not p:
        flash("Partita non trovata.", "error")
        return redirect(url_for("index"))
    if not is_admin() and p.get("user_id", 1) != uid:
        flash("Partita non trovata.", "error")
        return redirect(url_for("index"))
    quote = _quote_partita(p)
    scommesse = scommesse_per_partita(partita_id, uid)
    esito_label = {0: "1", 1: "X", 2: "2"}.get(p.get("esito"), None)
    return render_template("partita.html", partita=p, quote=quote, scommesse=scommesse, esito_label=esito_label)


@app.route("/partita/<int:partita_id>/scommessa", methods=["POST"])
@login_required
def scommetti(partita_id):
    """Registra una scommessa sulla partita."""
    p = get_partita(partita_id)
    if not p:
        flash("Partita non trovata.", "error")
        return redirect(url_for("index"))
    if p.get("esito") is not None:
        flash("La partita è già terminata, non puoi più scommettere.", "error")
        return redirect(url_for("partita", partita_id=partita_id))
    quote = _quote_partita(p)
    tipo = request.form.get("tipo", "")
    TIPI_SCOMMESSA = ("1", "X", "2", "1X", "X2", "12",
                      "Over1.5", "Under1.5", "Over2.5", "Under2.5", "Over3.5", "Under3.5")
    if tipo not in TIPI_SCOMMESSA:
        flash("Tipo di scommessa non valido.", "error")
        return redirect(url_for("partita", partita_id=partita_id))
    try:
        puntata = float(request.form.get("puntata", 0))
    except ValueError:
        puntata = 0
    if puntata <= 0:
        flash("La puntata deve essere maggiore di zero.", "error")
        return redirect(url_for("partita", partita_id=partita_id))
    quota = quote.get(tipo, 0)
    uid = _user_id()
    if not is_admin() and p.get("user_id", 1) != uid:
        flash("Partita non trovata.", "error")
        return redirect(url_for("index"))
    bankroll = carica_bankroll(uid)
    if puntata > bankroll:
        flash(f"Bankroll insufficiente. Hai €{bankroll:,.2f}.", "error")
        return redirect(url_for("partita", partita_id=partita_id))
    salva_bankroll(bankroll - puntata, uid)
    aggiungi_scommessa({
        "partita_id": partita_id,
        "partita_nome": p["nome"],
        "tipo": tipo,
        "quota": quota,
        "puntata": puntata,
        "esito_partita": None,
        "vinto": None,
        "vincita": None,
    }, user_id=uid)
    flash(f"Scommessa registrata: {tipo} @ {quota:.2f} per €{puntata:,.2f}")
    return redirect(url_for("partita", partita_id=partita_id))


@app.route("/partita/<int:partita_id>/simula", methods=["POST"])
@login_required
def simula(partita_id):
    """Simula l'esito della partita e aggiorna le scommesse."""
    p = get_partita(partita_id)
    if not p:
        flash("Partita non trovata.", "error")
        return redirect(url_for("index"))
    if p.get("esito") is not None:
        flash("La partita è già stata simulata.", "info")
        return redirect(url_for("partita", partita_id=partita_id))
    uid = _user_id()
    if not is_admin() and p.get("user_id", 1) != uid:
        flash("Partita non trovata.", "error")
        return redirect(url_for("index"))
    esito = simula_esito(p["probabilita"])
    aggiorna_partita(partita_id, esito=esito)
    esito_label = ["1", "X", "2"][esito]
    gol_tot = simula_gol(50, 50)
    from web_storage import salva_scommesse
    tutte = carica_scommesse(None)
    bankroll_updates = {}
    for s in tutte:
        if s.get("partita_id") == partita_id:
            if _is_ou(s.get("tipo", "")):
                s["esito_partita"] = f"{gol_tot} gol"
                s["vinto"] = scommessa_ou_vincente(s["tipo"], gol_tot)
            else:
                s["esito_partita"] = esito_label
                s["vinto"] = scommessa_vincente(s["tipo"], esito)
            s["vincita"] = calcola_vincita(s["puntata"], s["quota"]) if s["vinto"] else 0
            suid = s.get("user_id", 1)
            bankroll_updates[suid] = bankroll_updates.get(suid, carica_bankroll(suid)) + s["vincita"]
    for suid, val in bankroll_updates.items():
        salva_bankroll(val, suid)
    salva_scommesse(tutte)
    flash(f"Esito simulato: {esito_label} ({gol_tot} gol)")
    return redirect(url_for("partita", partita_id=partita_id))


@app.route("/scommessa/<int:scommessa_id>/elimina", methods=["POST"])
@login_required
def scommessa_elimina(scommessa_id: int):
    """Elimina una scommessa singola. Se era in attesa, restituisce la puntata al bankroll."""
    uid = _user_id()
    scommessa = next((s for s in carica_scommesse(None) if s.get("id") == scommessa_id), None)
    if not scommessa:
        flash("Scommessa non trovata.", "error")
        return redirect(request.referrer or url_for("index"))
    if scommessa.get("user_id", 1) != uid and not is_admin():
        flash("Non autorizzato.", "error")
        return redirect(request.referrer or url_for("index"))
    rimuovi_scommessa(scommessa_id)
    if scommessa.get("vinto") is None:
        suid = scommessa.get("user_id", 1)
        bankroll = carica_bankroll(suid)
        salva_bankroll(bankroll + scommessa.get("puntata", 0), suid)
        flash(f"Scommessa eliminata. Rimborsati €{scommessa.get('puntata', 0):,.2f}.")
    else:
        flash("Scommessa eliminata.")
    return redirect(request.referrer or url_for("index"))


@app.route("/cronologia")
@login_required
def cronologia():
    """Cronologia scommesse e schedine con esiti."""
    uid = _user_id()
    scommesse = carica_scommesse(uid)
    schedine = carica_schedine(uid)
    campionato = carica_campionato()
    _arricchisci_schedine_con_esiti(schedine, campionato)
    return render_template("cronologia.html", scommesse=scommesse, schedine=schedine)


# =============================================================================
# VIRTUALI - Campionato simulato
# =============================================================================


def _classifica_ordinata(campionato: dict) -> list[tuple[int, str, dict]]:
    """Restituisce classifica ordinata: [(pos, nome, dati), ...]."""
    if not campionato:
        return []
    squadre = campionato["squadre"]
    cl = campionato.get("classifica", {})
    righe = []
    for i in range(len(squadre)):
        c = cl.get(str(i), {"punti": 0, "vittorie": 0, "pareggi": 0, "sconfitte": 0})
        righe.append((i, squadre[i]["nome"], c))
    righe.sort(key=lambda x: (-x[2]["punti"], -x[2]["vittorie"]))
    return [(pos, nome, dati) for pos, (_, nome, dati) in enumerate(righe, 1)]


@app.route("/virtuali/inizializza", methods=["POST"])
@login_required
def virtuali_inizializza():
    """Inizializza un nuovo campionato dalle squadre in squadre.json."""
    try:
        squadre = carica_squadre()
        if len(squadre) < 2:
            flash("Servono almeno 2 squadre in squadre.json. Aggiungile dal menu principale.", "error")
            return redirect(url_for("virtuali"))
        inizializza_campionato()
        flash(f"Campionato creato con {len(squadre)} squadre. Buone scommesse!")
        return redirect(url_for("virtuali"))
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("virtuali"))


@app.route("/virtuali")
@login_required
def virtuali():
    """Sezione virtuali: campionato con partite della prossima giornata e scommesse."""
    uid = _user_id()
    campionato = carica_campionato()
    if not campionato:
        squadre = carica_squadre()
        return render_template("virtuali.html", campionato=None, partite_giornata=[], classifica=[],
                              squadre=squadre, countdown_sec=0, calendario_risultati=[])
    gc = campionato.get("giornata_corrente", 0)
    calendario = campionato.get("calendario", [])
    squadre = campionato["squadre"]
    classifica = _classifica_ordinata(campionato)
    partite_giornata = []
    if gc < len(calendario):
        for ic, it in calendario[gc]:
            fc = squadre[ic]["forza"]
            ft = squadre[it]["forza"]
            prob, quote = campionato_quote_partita(fc, ft)
            q_doppie = quote_doppie_da_probabilita(prob, 0.05)
            q_ou = quote_over_under(fc, ft, 0.05)
            partite_giornata.append({
                "ic": ic, "it": it,
                "casa": squadre[ic]["nome"], "trasferta": squadre[it]["nome"],
                "quote": {
                    "1": round(quote[0], 2), "X": round(quote[1], 2), "2": round(quote[2], 2),
                    "1X": round(q_doppie["1X"], 2), "X2": round(q_doppie["X2"], 2), "12": round(q_doppie["12"], 2),
                    **q_ou,
                },
            })
    countdown_sec = 180 if partite_giornata else 0
    schedine_giornata = [s for s in carica_schedine(uid) if s.get("giornata") == gc + 1]
    _arricchisci_schedine_con_esiti(schedine_giornata, campionato)
    calendario_risultati = _calendario_risultati(campionato, partite_giornata)
    return render_template("virtuali.html", campionato=campionato, partite_giornata=partite_giornata,
                          classifica=classifica, giornata_num=gc + 1, tot_giornate=len(calendario),
                          schedine=schedine_giornata, countdown_sec=countdown_sec,
                          calendario_risultati=calendario_risultati)


def _quota_per_tipo(fc: float, ft: float, tipo: str) -> float:
    """Restituisce la quota per un tipo di scommessa."""
    if tipo in ("1", "X", "2"):
        _, quote = campionato_quote_partita(fc, ft)
        return quote[["1", "X", "2"].index(tipo)]
    if tipo in ("1X", "X2", "12"):
        prob, _ = campionato_quote_partita(fc, ft)
        qd = quote_doppie_da_probabilita(prob, 0.05)
        return qd[tipo]
    if tipo.startswith("Over") or tipo.startswith("Under"):
        qou = quote_over_under(fc, ft, 0.05)
        return qou.get(tipo, 1.0)
    return 1.0


def _is_ou(tipo: str) -> bool:
    return tipo.startswith("Over") or tipo.startswith("Under")


def _arricchisci_schedine_con_esiti(schedine: list[dict], campionato: dict | None) -> None:
    """Per schedine risolte senza corretto/esito_reale, li calcola dai risultati del campionato."""
    if not campionato:
        return
    risultati_tutti = campionato.get("risultati", [])
    for sch in schedine:
        if sch.get("vinto") is None:
            continue
        g = sch.get("giornata")
        risultati_g = [r for r in risultati_tutti if r.get("giornata") == g]
        if not risultati_g:
            continue
        for sel in sch.get("selezioni", []):
            if "corretto" in sel:
                continue
            for r in risultati_g:
                if r.get("casa") == sel.get("ic") and r.get("trasferta") == sel.get("it"):
                    if _is_ou(sel.get("tipo", "")):
                        continue
                    else:
                        esito = r.get("esito", 1)
                        sel["esito_reale"] = ["1", "X", "2"][esito]
                        sel["corretto"] = scommessa_vincente(sel["tipo"], esito)
                    break


@app.route("/virtuali/schedina", methods=["POST"])
@login_required
def virtuali_schedina():
    """Registra una schedina."""
    campionato = carica_campionato()
    if not campionato:
        flash("Nessun campionato caricato.", "error")
        return redirect(url_for("virtuali"))
    gc = campionato.get("giornata_corrente", 0)
    calendario = campionato.get("calendario", [])
    if gc >= len(calendario):
        flash("Il campionato è concluso.", "error")
        return redirect(url_for("virtuali"))
    squadre = campionato["squadre"]
    partite_giornata = [(ic, it) for ic, it in calendario[gc]]
    selezioni = []
    quota_tot = 1.0
    for ic, it in partite_giornata:
        key = f"sel_{ic}_{it}"
        tipo = request.form.get(key)
        if tipo and tipo in TIPI_SCHEDINA:
            fc, ft = squadre[ic]["forza"], squadre[it]["forza"]
            q = _quota_per_tipo(fc, ft, tipo)
            nome = f"{squadre[ic]['nome']} - {squadre[it]['nome']}"
            selezioni.append({"ic": ic, "it": it, "partita_nome": nome, "tipo": tipo, "quota": round(q, 2)})
            quota_tot *= q
    if len(selezioni) < 1:
        flash("Seleziona almeno un esito per creare la schedina.", "error")
        return redirect(url_for("virtuali"))
    try:
        puntata = float(request.form.get("puntata", 0))
    except ValueError:
        puntata = 0
    if puntata <= 0:
        flash("La puntata deve essere maggiore di zero.", "error")
        return redirect(url_for("virtuali"))
    uid = _user_id()
    bankroll = carica_bankroll(uid)
    if puntata > bankroll:
        flash(f"Bankroll insufficiente. Hai €{bankroll:,.2f}.", "error")
        return redirect(url_for("virtuali"))
    salva_bankroll(bankroll - puntata, uid)
    vincita_pot = round(puntata * quota_tot, 2)
    aggiungi_schedina({
        "giornata": gc + 1,
        "selezioni": selezioni,
        "quota_combinata": round(quota_tot, 2),
        "puntata": puntata,
        "vincita_potenziale": vincita_pot,
    }, user_id=uid)
    flash(f"Schedina piazzata! Vincita potenziale: €{vincita_pot:,.2f}")
    return redirect(url_for("virtuali"))


@app.route("/virtuali/gioca-giornata", methods=["POST"])
@login_required
def virtuali_gioca_giornata():
    """Gioca la giornata corrente e aggiorna le scommesse virtuali."""
    campionato = carica_campionato()
    if not campionato:
        flash("Nessun campionato caricato.", "error")
        return redirect(url_for("virtuali"))
    gc = campionato.get("giornata_corrente", 0)
    if gc >= len(campionato.get("calendario", [])):
        flash("Il campionato è concluso.", "info")
        return redirect(url_for("virtuali"))
    risultati = gioca_giornata(campionato)
    squadre = campionato["squadre"]
    # Simula gol per ogni partita (per O/U)
    gol_per_partita = {}
    for r in risultati:
        fc = squadre[r["casa"]]["forza"]
        ft = squadre[r["trasferta"]]["forza"]
        gol_per_partita[(r["casa"], r["trasferta"])] = simula_gol(fc, ft)
    # Risolvi schedine (tutte, da tutti gli utenti)
    tutte_schedine = carica_schedine(None)
    bankroll_updates = {}
    for sch in tutte_schedine:
        if sch.get("giornata") != gc + 1 or sch.get("vinto") is not None:
            continue
        eventi_sbagliati = 0
        for sel in sch.get("selezioni", []):
            for r in risultati:
                if r["casa"] == sel["ic"] and r["trasferta"] == sel["it"]:
                    if _is_ou(sel["tipo"]):
                        gol = gol_per_partita.get((r["casa"], r["trasferta"]), 0)
                        corretto = scommessa_ou_vincente(sel["tipo"], gol)
                        esito_reale = f"{gol} gol"
                    else:
                        esito_reale = ["1", "X", "2"][r["esito"]]
                        corretto = scommessa_vincente(sel["tipo"], r["esito"])
                    sel["corretto"] = corretto
                    sel["esito_reale"] = esito_reale
                    if not corretto:
                        eventi_sbagliati += 1
                    break
        sch["vinto"] = eventi_sbagliati == 0
        sch["vincita"] = calcola_vincita(sch["puntata"], sch["quota_combinata"]) if sch["vinto"] else 0
        sch["eventi_sbagliati"] = eventi_sbagliati
        if sch["vinto"]:
            suid = sch.get("user_id", 1)
            bankroll_updates[suid] = bankroll_updates.get(suid, carica_bankroll(suid)) + sch["vincita"]
    for suid, val in bankroll_updates.items():
        salva_bankroll(val, suid)
    salva_schedine(tutte_schedine)
    flash(f"Giornata {gc + 1} giocata!")
    return redirect(url_for("virtuali"))


@app.route("/virtuali/schedina/<int:schedina_id>/elimina", methods=["POST"])
@login_required
def virtuali_schedina_elimina(schedina_id: int):
    """Elimina una schedina. Se era in attesa, restituisce la puntata al bankroll."""
    uid = _user_id()
    schedina = next((s for s in carica_schedine(None) if s.get("id") == schedina_id), None)
    if not schedina:
        flash("Schedina non trovata.", "error")
        return redirect(request.referrer or url_for("virtuali"))
    if schedina.get("user_id", 1) != uid and not is_admin():
        flash("Non autorizzato.", "error")
        return redirect(request.referrer or url_for("virtuali"))
    _, era_in_attesa = rimuovi_schedina(schedina_id)
    if era_in_attesa:
        suid = schedina.get("user_id", 1)
        bankroll = carica_bankroll(suid)
        salva_bankroll(bankroll + schedina.get("puntata", 0), suid)
        flash(f"Schedina eliminata. Rimborsati €{schedina.get('puntata', 0):,.2f}.")
    else:
        flash("Schedina eliminata.")
    return redirect(request.referrer or url_for("virtuali"))


@app.route("/virtuali/schedina/<int:schedina_id>/evento/<int:ic>/<int:it>/elimina", methods=["POST"])
@login_required
def virtuali_schedina_evento_elimina(schedina_id: int, ic: int, it: int):
    """Elimina un singolo evento da una schedina in attesa."""
    uid = _user_id()
    schedina_pre = next((s for s in carica_schedine(None) if s.get("id") == schedina_id), None)
    if not schedina_pre or (schedina_pre.get("user_id", 1) != uid and not is_admin()):
        flash("Non autorizzato.", "error")
        return redirect(request.referrer or url_for("virtuali"))
    schedina, puntata_rimborso = rimuovi_evento_schedina(schedina_id, ic, it)
    if schedina is None and puntata_rimborso <= 0:
        flash("Operazione non possibile.", "error")
        return redirect(request.referrer or url_for("virtuali"))
    if puntata_rimborso > 0:
        suid = schedina_pre.get("user_id", 1)
        bankroll = carica_bankroll(suid)
        salva_bankroll(bankroll + puntata_rimborso, suid)
        flash(f"Schedina vuota eliminata. Rimborsati €{puntata_rimborso:,.2f}.")
    else:
        flash("Evento rimosso dalla schedina.")
    return redirect(request.referrer or url_for("virtuali"))


# =============================================================================
# ADMIN
# =============================================================================


@app.route("/admin")
@admin_required
def admin_dashboard():
    """Dashboard admin."""
    utenti = carica_utenti()
    partite_tutte = carica_partite(None)
    scommesse_tutte = carica_scommesse(None)
    bankroll_per_user = {}
    for u in utenti:
        bankroll_per_user[str(u["id"])] = carica_bankroll(u["id"])
    return render_template("admin_dashboard.html",
                          utenti=utenti,
                          partite_totali=len(partite_tutte),
                          scommesse_totali=len(scommesse_tutte),
                          bankroll_per_user=bankroll_per_user)


@app.route("/admin/utenti")
@admin_required
def admin_utenti():
    """Gestione utenti."""
    return render_template("admin_utenti.html", utenti=carica_utenti())


@app.route("/admin/utente/crea", methods=["POST"])
@admin_required
def admin_utente_crea():
    """Crea nuovo utente."""
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    ruolo = request.form.get("ruolo", "user")
    if not username or len(username) < 2:
        flash("Username deve avere almeno 2 caratteri.", "error")
        return redirect(url_for("admin_utenti"))
    if len(password) < 4:
        flash("Password deve avere almeno 4 caratteri.", "error")
        return redirect(url_for("admin_utenti"))
    try:
        crea_utente(username, generate_password_hash(password), ruolo)
        flash(f"Utente '{username}' creato.")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("admin_utenti"))


@app.route("/admin/utente/<int:user_id>/ruolo", methods=["POST"])
@admin_required
def admin_utente_ruolo(user_id: int):
    """Cambia ruolo utente."""
    ruolo = request.form.get("ruolo", "user")
    if aggiorna_ruolo_utente(user_id, ruolo):
        flash("Ruolo aggiornato.")
    else:
        flash("Utente non trovato.", "error")
    return redirect(url_for("admin_utenti"))


def main():
    import webbrowser
    from threading import Timer

    def apri_browser():
        webbrowser.open("http://127.0.0.1:5000")

    Timer(1.5, apri_browser).start()
    app.run(debug=True, port=5000)


if __name__ == "__main__":
    main()
