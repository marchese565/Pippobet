"""
BetOdds Simulator - Modulo campionato.
Gestisce squadre con forza, quote dinamiche, calendario e classifica.
Simula un campionato stile Serie A (20 squadre, 38 giornate).
"""

import random

from odds import quote_bookmaker_da_probabilita, calcola_profitto, simula_gol
from storage import (
    carica_squadre,
    salva_squadre,
    carica_campionato,
    salva_campionato,
    aggiungi_evento_sessione,
)

DRAW_PROB_DEFAULT = 0.25  # probabilità di pareggio di base
MARGINE_BOOK = 0.05
MIN_SQUADRE = 2
MAX_SQUADRE = 20
FORZA_MIN = 1
FORZA_MAX = 100


def probabilità_partita(forza_casa: float, forza_trasferta: float, prob_pareggio: float = DRAW_PROB_DEFAULT) -> list[float]:
    """
    Calcola le probabilità 1, X, 2 in base alle forze delle squadre.
    P(1) e P(2) proporzionali alle forze; P(X) = prob_pareggio.
    """
    if forza_casa <= 0 or forza_trasferta <= 0:
        raise ValueError("Le forze devono essere positive")
    if prob_pareggio < 0 or prob_pareggio >= 1:
        raise ValueError("prob_pareggio deve essere tra 0 e 1 (escluso)")
    somma = forza_casa + forza_trasferta
    resto = 1.0 - prob_pareggio
    p1 = resto * forza_casa / somma
    p2 = resto * forza_trasferta / somma
    px = prob_pareggio
    return [p1, px, p2]


def quote_partita(forza_casa: float, forza_trasferta: float, margine: float = MARGINE_BOOK, prob_pareggio: float = DRAW_PROB_DEFAULT) -> tuple[list[float], list[float]]:
    """Restituisce (probabilità, quote_book) per una partita."""
    prob = probabilità_partita(forza_casa, forza_trasferta, prob_pareggio)
    quote = quote_bookmaker_da_probabilita(prob, margine)
    return (prob, quote)


def simula_risultato(prob: list[float], seed: int | None = None) -> int:
    """
    Simula l'esito della partita (0=1, 1=X, 2=2) in base alle probabilità.
    Restituisce 0 (casa), 1 (pareggio), 2 (trasferta).
    """
    if seed is not None:
        random.seed(seed)
    r = random.random()
    cum = 0.0
    for i, p in enumerate(prob):
        cum += p
        if r < cum:
            return i
    return 2


def aggiungi_squadra(nome: str, forza: float) -> None:
    """Aggiunge una squadra all'elenco."""
    squadre = carica_squadre()
    if len(squadre) >= MAX_SQUADRE:
        raise ValueError(f"Numero massimo di squadre: {MAX_SQUADRE}")
    if forza < FORZA_MIN or forza > FORZA_MAX:
        raise ValueError(f"Forza deve essere tra {FORZA_MIN} e {FORZA_MAX}")
    nome = nome.strip()
    if not nome:
        raise ValueError("Il nome della squadra non può essere vuoto")
    for s in squadre:
        if s["nome"].lower() == nome.lower():
            raise ValueError(f"Squadra '{nome}' già presente")
    squadre.append({"nome": nome, "forza": float(forza)})
    salva_squadre(squadre)


def _genera_calendario(squadre: list[dict]) -> list[list[tuple[int, int]]]:
    """
    Genera il calendario round-robin: ogni squadra gioca contro ogni altra in casa e in trasferta.
    Restituisce lista di giornate; ogni giornata è lista di (indice_casa, indice_trasferta).
    """
    n = len(squadre)
    if n < 2:
        return []
    # algoritmo round-robin classico
    indici = list(range(n))
    if n % 2 == 1:
        indici.append(-1)  # turno
    giornate = []
    for _ in range(len(indici) - 1):
        giornata = []
        for i in range(len(indici) // 2):
            a, b = indici[i], indici[len(indici) - 1 - i]
            if a >= 0 and b >= 0:
                giornata.append((a, b))
        giornate.append(giornata)
        # ruota
        fissi = indici[0]
        indici = [indici[0]] + [indici[-1]] + indici[1:-1]
    # ritorno: inverti casa/trasferta
    giornate_ritorno = []
    for g in giornate:
        giornate_ritorno.append([(b, a) for a, b in g])
    return giornate + giornate_ritorno


def inizializza_campionato() -> dict:
    """Crea un nuovo campionato con calendario e classifica vuota."""
    squadre = carica_squadre()
    if len(squadre) < MIN_SQUADRE:
        raise ValueError(f"Servono almeno {MIN_SQUADRE} squadre per avviare il campionato")
    calendario = _genera_calendario(squadre)
    classifica = {str(i): {"punti": 0, "vittorie": 0, "pareggi": 0, "sconfitte": 0} for i in range(len(squadre))}
    risultati = []  # lista di {giornata, casa, trasferta, esito, prob, quote}
    campionato = {
        "squadre": squadre,
        "calendario": [[[int(a), int(b)] for a, b in g] for g in calendario],
        "classifica": classifica,
        "risultati": risultati,
        "giornata_corrente": 0,
    }
    salva_campionato(campionato)
    aggiungi_evento_sessione("campionato_inizializzato", {
        "squadre": len(squadre),
        "giornate": len(calendario),
    })
    return campionato


def gioca_giornata(campionato: dict | None = None, margine: float = MARGINE_BOOK, prob_pareggio: float = DRAW_PROB_DEFAULT) -> list[dict]:
    """
    Simula una giornata di campionato. Restituisce la lista dei risultati della giornata.
    """
    if campionato is None:
        campionato = carica_campionato()
    if not campionato:
        raise ValueError("Nessun campionato attivo. Inizializzane uno.")
    gc = campionato["giornata_corrente"]
    calendario = campionato["calendario"]
    if gc >= len(calendario):
        raise ValueError("Campionato già concluso.")
    squadre = campionato["squadre"]
    classifica = campionato["classifica"]
    partite_giornata = calendario[gc]
    risultati_giornata = []
    for ic, it in partite_giornata:
        fc = squadre[ic]["forza"]
        ft = squadre[it]["forza"]
        prob, quote = quote_partita(fc, ft, margine, prob_pareggio)
        esito = simula_risultato(prob)
        gol_tot = simula_gol(fc, ft)
        if gol_tot == 0 and esito != 1:
            gol_casa, gol_trasf = (1, 0) if esito == 0 else (0, 1)
        elif esito == 0:
            gol_casa, gol_trasf = (gol_tot + 1) // 2, gol_tot // 2
            if gol_casa <= gol_trasf:
                gol_casa, gol_trasf = gol_trasf + 1, gol_trasf
        elif esito == 1:
            gol_casa = gol_trasf = gol_tot // 2
            if gol_tot % 2:
                gol_casa = gol_trasf = 1
        else:
            gol_casa, gol_trasf = gol_tot // 2, (gol_tot + 1) // 2
            if gol_trasf <= gol_casa:
                gol_casa, gol_trasf = gol_casa, gol_casa + 1
        risultati_giornata.append({
            "casa": ic, "trasferta": it, "esito": esito,
            "gol_casa": gol_casa, "gol_trasferta": gol_trasf,
            "prob": prob, "quote": quote,
            "nome_casa": squadre[ic]["nome"], "nome_trasferta": squadre[it]["nome"],
        })
        # aggiorna classifica
        if esito == 0:
            classifica[str(ic)]["punti"] += 3
            classifica[str(ic)]["vittorie"] += 1
            classifica[str(it)]["sconfitte"] += 1
        elif esito == 1:
            classifica[str(ic)]["punti"] += 1
            classifica[str(it)]["punti"] += 1
            classifica[str(ic)]["pareggi"] += 1
            classifica[str(it)]["pareggi"] += 1
        else:
            classifica[str(it)]["punti"] += 3
            classifica[str(it)]["vittorie"] += 1
            classifica[str(ic)]["sconfitte"] += 1
        campionato["risultati"].append({
            "giornata": gc + 1, "casa": ic, "trasferta": it, "esito": esito,
            "gol_casa": gol_casa, "gol_trasferta": gol_trasf,
            "prob": prob, "quote": quote,
        })
        aggiungi_evento_sessione("partita_campionato", {
            "giornata": gc + 1,
            "partita": f"{squadre[ic]['nome']} - {squadre[it]['nome']}",
            "esito": ["1", "X", "2"][esito],
            "quote": quote,
        })
    campionato["giornata_corrente"] = gc + 1
    salva_campionato(campionato)
    return risultati_giornata


def stampa_classifica(campionato: dict | None = None) -> None:
    """Stampa la classifica ordinata per punti."""
    if campionato is None:
        campionato = carica_campionato()
    if not campionato:
        print("  Nessun campionato attivo.")
        return
    squadre = campionato["squadre"]
    classifica = campionato["classifica"]
    # ordina per punti (decrescente)
    righe = []
    for i in range(len(squadre)):
        c = classifica.get(str(i), {"punti": 0, "vittorie": 0, "pareggi": 0, "sconfitte": 0})
        righe.append((i, squadre[i]["nome"], c["punti"], c["vittorie"], c["pareggi"], c["sconfitte"]))
    righe.sort(key=lambda x: (-x[2], -x[3]))
    print("\n" + "-" * 55)
    print("  CLASSIFICA")
    print("-" * 55)
    print(f"  {'Pos':<4} {'Squadra':<25} {'Pt':>4} {'V':>3} {'N':>3} {'P':>3}")
    print("-" * 55)
    for pos, (_, nome, pt, v, n, p) in enumerate(righe, 1):
        print(f"  {pos:<4} {nome:<25} {pt:>4} {v:>3} {n:>3} {p:>3}")
    print("-" * 55)


def stampa_giornata(risultati: list[dict]) -> None:
    """Stampa i risultati di una giornata con quote."""
    if not risultati:
        return
    print("\n  Risultati e quote:")
    for r in risultati:
        esito_str = ["1", "X", "2"][r["esito"]]
        q = r["quote"]
        print(f"    {r['nome_casa']} - {r['nome_trasferta']}: {esito_str}  (quote: {q[0]:.2f} {q[1]:.2f} {q[2]:.2f})")


def stato_campionato(campionato: dict | None = None) -> dict:
    """Restituisce info sullo stato del campionato."""
    if campionato is None:
        campionato = carica_campionato()
    if not campionato:
        return {"attivo": False}
    gc = campionato["giornata_corrente"]
    tot = len(campionato["calendario"])
    return {"attivo": True, "giornata": gc, "totale_giornate": tot, "finito": gc >= tot}


def simula_bankroll_sul_campionato(
    bankroll_iniziale: float,
    puntata: float,
    puntata_percentuale: bool = False,
    margine: float = MARGINE_BOOK,
    prob_pareggio: float = DRAW_PROB_DEFAULT,
    seed: int | None = None,
) -> list[dict]:
    """
    Simula l'andamento del bankroll scommettendo su tutte le partite del campionato.
    In ogni partita si scommette sempre sull'esito con probabilità maggiore (il favorito).
    Il risultato della partita è simulato casualmente in base alle probabilità.

    Restituisce una lista di dict: [{n, partita, prob, quote, scommessa_esito, esito_reale, vinto, profitto, bankroll}, ...]
    """
    if seed is not None:
        random.seed(seed)
    squadre = carica_squadre()
    if len(squadre) < MIN_SQUADRE:
        raise ValueError(f"Servono almeno {MIN_SQUADRE} squadre. Aggiungile e inizializza il campionato.")
    calendario = _genera_calendario(squadre)
    storico = []
    bankroll = bankroll_iniziale
    n = 0
    for giornata in calendario:
        for ic, it in giornata:
            n += 1
            fc = squadre[ic]["forza"]
            ft = squadre[it]["forza"]
            prob, quote = quote_partita(fc, ft, margine, prob_pareggio)
            # Scommessa sempre sul favorito (probabilità massima)
            scommessa_esito = int(max(range(3), key=lambda i: prob[i]))
            quota_scommessa = quote[scommessa_esito]
            if puntata_percentuale:
                puntata_eff = bankroll * puntata
            else:
                puntata_eff = min(puntata, bankroll)
            if puntata_eff <= 0:
                storico.append({
                    "n": n, "partita": f"{squadre[ic]['nome']} - {squadre[it]['nome']}",
                    "prob": prob, "quote": quote, "scommessa_esito": scommessa_esito,
                    "esito_reale": None, "vinto": False, "profitto": 0.0, "bankroll": bankroll,
                })
                continue
            esito_reale = simula_risultato(prob)
            vinto = esito_reale == scommessa_esito
            profitto = calcola_profitto(puntata_eff, quota_scommessa, vinto)
            bankroll += profitto
            storico.append({
                "n": n,
                "partita": f"{squadre[ic]['nome']} - {squadre[it]['nome']}",
                "prob": prob,
                "quote": quote,
                "scommessa_esito": scommessa_esito,
                "esito_reale": esito_reale,
                "vinto": vinto,
                "profitto": profitto,
                "bankroll": bankroll,
            })
    if storico:
        ultimo = storico[-1]
        vittorie = sum(1 for s in storico if s.get("vinto"))
        aggiungi_evento_sessione("simulazione_bankroll_campionato", {
            "bankroll_iniziale": bankroll_iniziale,
            "bankroll_finale": ultimo["bankroll"],
            "partite": len(storico),
            "vittorie": vittorie,
        })
    return storico


def stampa_simulazione_bankroll(
    storico: list[dict],
    bankroll_iniziale: float,
    max_righe: int = 15,
    larghezza_grafico: int = 50,
    altezza_grafico: int = 8,
) -> None:
    """Stampa riepilogo e grafico ASCII dell'andamento del bankroll (scommessa sul favorito)."""
    if not storico:
        print("  Nessuna partita simulata.")
        return
    ultimo = storico[-1]
    bankroll_finale = ultimo["bankroll"]
    variaz = bankroll_finale - bankroll_iniziale
    variaz_pct = (variaz / bankroll_iniziale) * 100 if bankroll_iniziale > 0 else 0
    vittorie = sum(1 for s in storico if s.get("vinto"))
    totali = sum(1 for s in storico if s.get("esito_reale") is not None)
    print("\n--- Bankroll sul campionato (scommessa sul favorito) ---")
    print(f"  Bankroll iniziale: {bankroll_iniziale:,.2f}")
    print(f"  Bankroll finale:   {bankroll_finale:,.2f}")
    print(f"  Variazione:        {variaz:+,.2f} ({variaz_pct:+.1f}%)")
    print(f"  Vittorie:          {vittorie}/{totali}")
    print("\n  Dettaglio (prime partite):")
    esiti = ["1", "X", "2"]
    for s in storico[:max_righe]:
        bet = esiti[s["scommessa_esito"]]
        real = esiti[s["esito_reale"]] if s.get("esito_reale") is not None else "-"
        ok = "OK" if s.get("vinto") else "no"
        print(f"    {s['n']:>3}) {s['partita']:<30} scommessa: {bet}  esito: {real}  {ok}  bankroll: {s['bankroll']:,.0f}")
    if len(storico) > max_righe:
        print(f"    ... ({len(storico) - max_righe} altre partite)")
        print(f"    {storico[-1]['n']:>3}) {storico[-1]['partita']:<30} ...  bankroll: {storico[-1]['bankroll']:,.0f}")
    valori = [bankroll_iniziale] + [s["bankroll"] for s in storico]
    min_v, max_v = min(valori), max(valori)
    span = max_v - min_v if (max_v - min_v) > 0 else 1
    step = max(1, len(valori) // larghezza_grafico)
    campioni = [valori[i] for i in range(0, len(valori), step)]
    if valori[-1] != campioni[-1]:
        campioni.append(valori[-1])
    print("\n  Andamento bankroll:")
    righe = [[" "] * len(campioni) for _ in range(altezza_grafico)]
    for i, v in enumerate(campioni):
        pos = int((v - min_v) / span * (altezza_grafico - 1))
        pos = altezza_grafico - 1 - pos
        righe[pos][i] = "*"
    for r in righe:
        print("  |" + "".join(r) + "|")
    print("  +" + "-" * len(campioni) + "+")
    print(f"  0{' ' * (len(campioni) - 2)}{len(storico)} (partite)")
    print(f"  Min: {min_v:,.0f}  |  Max: {max_v:,.0f}\n")
