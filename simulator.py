"""
BetOdds Simulator - Modulo simulatore.
Simula un numero di scommesse casuali e mostra l'andamento del bankroll nel tempo.

Esecuzione:
  python simulator.py          → richiede parametri da terminale (numero scommesse, ecc.)
  python simulator.py --default  → simulazione con parametri predefiniti (100 scommesse)
"""

import random
import sys

from odds import calcola_profitto
from storage import aggiungi_evento_sessione

MIN_SCOMMESSE = 10
MAX_SCOMMESSE = 10000


def simula_scommesse(
    bankroll_iniziale: float,
    num_scommesse: int,
    puntata: float,
    probabilita_vittoria: float,
    quota_min: float,
    quota_max: float,
    puntata_percentuale: bool = False,
    seed: int | None = None,
) -> list[dict]:
    """
    Simula una serie di scommesse casuali e restituisce la cronologia.
    Le quote sono generate casualmente in [quota_min, quota_max] per ogni scommessa.

    Args:
        bankroll_iniziale: Capitale di partenza
        num_scommesse: Numero di scommesse da simulare
        puntata: Importo fisso o percentuale (se puntata_percentuale=True)
        probabilita_vittoria: Probabilità reale di vincere (0-1)
        quota_min: Quota minima (estremo inferiore del range)
        quota_max: Quota massima (estremo superiore del range)
        puntata_percentuale: Se True, puntata è % del bankroll corrente
        seed: Seed per riproducibilità (opzionale)

    Returns:
        Lista di dict: [{n, bankroll, puntata_eff, quota, vinto, profitto, bankroll_dopo}, ...]
    """
    if seed is not None:
        random.seed(seed)
    if bankroll_iniziale <= 0:
        raise ValueError("Il bankroll iniziale deve essere positivo")
    if num_scommesse < MIN_SCOMMESSE or num_scommesse > MAX_SCOMMESSE:
        raise ValueError(f"Il numero di scommesse deve essere tra {MIN_SCOMMESSE} e {MAX_SCOMMESSE}")
    if probabilita_vittoria < 0 or probabilita_vittoria > 1:
        raise ValueError("La probabilità di vittoria deve essere tra 0 e 1")
    if quota_min <= 0 or quota_max <= 0:
        raise ValueError("Le quote devono essere positive")
    if quota_min > quota_max:
        raise ValueError("quota_min deve essere <= quota_max")
    if puntata_percentuale and (puntata <= 0 or puntata > 1):
        raise ValueError("Con puntata percentuale, il valore deve essere tra 0 e 1")

    storico = []
    bankroll = bankroll_iniziale

    for n in range(1, num_scommesse + 1):
        if puntata_percentuale:
            puntata_eff = bankroll * puntata
        else:
            puntata_eff = min(puntata, bankroll)

        if puntata_eff <= 0:
            storico.append({
                "n": n,
                "bankroll": bankroll,
                "puntata_eff": 0.0,
                "quota": 0.0,
                "vinto": False,
                "profitto": 0.0,
                "bankroll_dopo": bankroll,
            })
            continue

        quota_eff = random.uniform(quota_min, quota_max)
        vinto = random.random() < probabilita_vittoria
        profitto = calcola_profitto(puntata_eff, quota_eff, vinto)
        bankroll_dopo = bankroll + profitto

        storico.append({
            "n": n,
            "bankroll": bankroll,
            "puntata_eff": puntata_eff,
            "quota": quota_eff,
            "vinto": vinto,
            "profitto": profitto,
            "bankroll_dopo": bankroll_dopo,
        })
        bankroll = bankroll_dopo

    return storico


def stampa_storico(
    storico: list[dict],
    bankroll_iniziale: float,
    dettaglio: bool = True,
    max_righe: int = 20,
) -> None:
    """
    Stampa l'andamento del bankroll e un riepilogo.

    Args:
        storico: Output di simula_scommesse()
        bankroll_iniziale: Capitale di partenza
        dettaglio: Se True, mostra ogni scommessa (limitato a max_righe)
        max_righe: Quante righe di dettaglio mostrare
    """
    if not storico:
        print("  Nessuna scommessa simulata.")
        return

    ultimo = storico[-1]
    bankroll_finale = ultimo["bankroll_dopo"]
    variaz = bankroll_finale - bankroll_iniziale
    variaz_pct = (variaz / bankroll_iniziale) * 100 if bankroll_iniziale > 0 else 0
    vittorie = sum(1 for s in storico if s["vinto"] and s["puntata_eff"] > 0)
    totali = sum(1 for s in storico if s["puntata_eff"] > 0)
    rate = (vittorie / totali * 100) if totali > 0 else 0

    print("\n--- Andamento bankroll ---")
    print(f"  Bankroll iniziale: {bankroll_iniziale:,.2f}")
    print(f"  Bankroll finale:   {bankroll_finale:,.2f}")
    print(f"  Variazione:        {variaz:+,.2f} ({variaz_pct:+.1f}%)")
    print(f"  Vittorie:          {vittorie}/{totali} ({rate:.1f}%)")

    if dettaglio and storico:
        print("\n--- Dettaglio scommesse ---")
        sep = "+" + "-" * 6 + "+" + "-" * 10 + "+" + "-" * 8 + "+" + "-" * 6 + "+" + "-" * 6 + "+" + "-" * 10 + "+"
        print(sep)
        print("| {:>4} | {:>8} | {:>6} | {:>6} | {:>4} | {:>8} |".format(
            "N", "Bankroll", "Puntata", "Quota", "Esito", "Dopo"
        ))
        print(sep)

        righe = storico[:max_righe]
        for s in righe:
            esito = "OK" if s["vinto"] else "no"
            print("| {:>4} | {:>8.2f} | {:>6.2f} | {:>6.2f} | {:>4} | {:>8.2f} |".format(
                s["n"], s["bankroll"], s["puntata_eff"], s["quota"], esito, s["bankroll_dopo"]
            ))
        if len(storico) > max_righe:
            s = storico[-1]
            esito = "OK" if s["vinto"] else "no"
            print("|  ... |   ...    |  ...   |  ...  | ... |   ...    |")
            print("| {:>4} | {:>8.2f} | {:>6.2f} | {:>6.2f} | {:>4} | {:>8.2f} |".format(
                s["n"], s["bankroll"], s["puntata_eff"], s["quota"], esito, s["bankroll_dopo"]
            ))
        print(sep)

    # Mini grafico ASCII dell'andamento
    print("\n--- Andamento nel tempo ---")
    _stampa_grafico_ascii(storico, bankroll_iniziale, larghezza=50, altezza=10)


def _stampa_grafico_ascii(
    storico: list[dict],
    bankroll_iniziale: float,
    larghezza: int = 50,
    altezza: int = 10,
) -> None:
    """Stampa un grafico ASCII dell'andamento del bankroll con scala valori (asse Y)."""
    valori = [bankroll_iniziale] + [s["bankroll_dopo"] for s in storico]
    if not valori:
        return
    min_v = min(valori)
    max_v = max(valori)
    span = max_v - min_v
    if span == 0:
        span = 1

    # Campioniamo per non avere troppi punti
    step = max(1, len(valori) // larghezza)
    campioni = [valori[i] for i in range(0, len(valori), step)]
    if valori[-1] != campioni[-1]:
        campioni.append(valori[-1])

    # Griglia: riga 0 = max, riga (altezza-1) = min
    righe = [[" "] * len(campioni) for _ in range(altezza)]
    for i, v in enumerate(campioni):
        pos = int((v - min_v) / span * (altezza - 1))
        pos = altezza - 1 - pos
        righe[pos][i] = "*"

    # Larghezza etichetta asse Y (es. "  1200" o "   950")
    if max_v >= 10000 or min_v >= 10000:
        fmt_y = "{:>6.0f}"
    elif max_v >= 1000 or min_v >= 1000:
        fmt_y = "{:>6.0f}"
    else:
        fmt_y = "{:>6.1f}"
    label_width = 6

    # Valore bankroll per ogni riga (dall'alto: max -> min)
    for r in range(altezza):
        val_riga = max_v - (r / max(altezza - 1, 1)) * span
        etichetta = fmt_y.format(val_riga)
        print(" " + etichetta + " |" + "".join(righe[r]) + "|")
    print(" " + " " * label_width + "+" + "-" * len(campioni) + "+")
    print(" " + " " * label_width + f" 0{' ' * (len(campioni) - 2)}{len(storico)} (scommessa)")
    print(f"  Min: {min_v:,.0f}  |  Max: {max_v:,.0f}\n")


def _modalita_interattiva() -> None:
    """Richiede i parametri da terminale e avvia la simulazione."""
    print("\n--- Simulatore scommesse casuali ---")
    try:
        bankroll = float(input("Bankroll iniziale [1000] > ").strip() or "1000")
        num = int(input(f"Numero scommesse ({MIN_SCOMMESSE}-{MAX_SCOMMESSE}) [100] > ").strip() or "100")
        if num < MIN_SCOMMESSE or num > MAX_SCOMMESSE:
            raise ValueError(f"Inserisci un numero tra {MIN_SCOMMESSE} e {MAX_SCOMMESSE}")

        print("\n  Strategia di puntata:")
        print("    1) Fissa - stesso importo per ogni scommessa")
        print("    2) Percentuale - % del bankroll corrente")
        strat = input("  Scelta [1] > ").strip() or "1"
        if strat == "2":
            puntata = float(input("  Percentuale bankroll (0-1, es: 0.02 = 2%) [0.02] > ").strip() or "0.02")
            puntata_perc = True
        else:
            puntata = float(input("  Importo fisso per scommessa [10] > ").strip() or "10")
            puntata_perc = False

        prob = float(input("Probabilità vittoria (0-1, es: 0.5) [0.5] > ").strip() or "0.5")
        print("\n  Range quote (dinamiche per ogni scommessa):")
        quota_min = float(input("  Quota minima [1.30] > ").strip() or "1.30")
        quota_max = float(input("  Quota massima [2.50] > ").strip() or "2.50")
        if quota_min > quota_max:
            raise ValueError("La quota minima deve essere <= quota massima")
    except ValueError as e:
        print(f"  Errore: {e}")
        return

    try:
        storico = simula_scommesse(
            bankroll_iniziale=bankroll,
            num_scommesse=num,
            puntata=puntata,
            probabilita_vittoria=prob,
            quota_min=quota_min,
            quota_max=quota_max,
            puntata_percentuale=puntata_perc,
        )
        stampa_storico(storico, bankroll, dettaglio=True, max_righe=15)
        _salva_simulazione_in_sessione(storico, bankroll, num, puntata, prob, quota_min, quota_max, puntata_perc)
    except ValueError as e:
        print(f"  Errore: {e}")


def _salva_simulazione_in_sessione(
    storico: list[dict],
    bankroll_iniziale: float,
    num_scommesse: int,
    puntata: float,
    probabilita_vittoria: float,
    quota_min: float,
    quota_max: float,
    puntata_percentuale: bool,
) -> None:
    """Salva i risultati della simulazione in session.json."""
    if not storico:
        return
    ultimo = storico[-1]
    bankroll_finale = ultimo["bankroll_dopo"]
    vittorie = sum(1 for s in storico if s["vinto"] and s["puntata_eff"] > 0)
    totali = sum(1 for s in storico if s["puntata_eff"] > 0)
    variaz = bankroll_finale - bankroll_iniziale
    variaz_pct = (variaz / bankroll_iniziale) * 100 if bankroll_iniziale > 0 else 0
    aggiungi_evento_sessione("simulazione", {
        "bankroll_iniziale": bankroll_iniziale,
        "bankroll_finale": bankroll_finale,
        "num_scommesse": num_scommesse,
        "vittorie": vittorie,
        "totali": totali,
        "variazione": variaz,
        "variazione_pct": variaz_pct,
        "puntata": puntata,
        "puntata_percentuale": puntata_percentuale,
        "probabilita_vittoria": probabilita_vittoria,
        "quota_min": quota_min,
        "quota_max": quota_max,
    })


def _modalita_default() -> None:
    """Esegue una simulazione con parametri di default."""
    storico = simula_scommesse(
        bankroll_iniziale=1000.0,
        num_scommesse=100,
        puntata=10.0,
        probabilita_vittoria=0.50,
        quota_min=1.30,
        quota_max=2.50,
        puntata_percentuale=False,
        seed=42,
    )
    stampa_storico(storico, 1000.0, dettaglio=True, max_righe=15)
    _salva_simulazione_in_sessione(
        storico, 1000.0, 100, 10.0, 0.50, 1.30, 2.50, False
    )


if __name__ == "__main__":
    if "--default" in sys.argv or "-d" in sys.argv:
        _modalita_default()
    else:
        _modalita_interattiva()
