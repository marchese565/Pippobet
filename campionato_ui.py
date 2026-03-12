"""
BetOdds Simulator - Interfaccia utente per il campionato.
"""

from campionato import (
    aggiungi_squadra,
    carica_squadre,
    carica_campionato,
    inizializza_campionato,
    gioca_giornata,
    stampa_classifica,
    stampa_giornata,
    stato_campionato,
    simula_bankroll_sul_campionato,
    stampa_simulazione_bankroll,
    MIN_SQUADRE,
    MAX_SQUADRE,
    FORZA_MIN,
    FORZA_MAX,
)


def _menu_campionato() -> str:
    print("\n--- Campionato ---")
    print("  1) Aggiungi squadra")
    print("  2) Lista squadre")
    print("  3) Inizializza campionato")
    print("  4) Gioca una giornata")
    print("  5) Gioca tutte le giornate rimanenti")
    print("  6) Classifica")
    print("  7) Simula bankroll (scommetti sempre sul favorito)")
    print("  8) Torna al menu principale")
    return input("Scelta > ").strip()


def _azione_aggiungi_squadra() -> None:
    print("\n--- Aggiungi squadra ---")
    print(f"  Forza: {FORZA_MIN}-{FORZA_MAX} (es. 75 per una squadra media-alta)")
    nome = input("  Nome squadra > ").strip()
    if nome.lower() == "q":
        return
    try:
        forza = float(input(f"  Forza ({FORZA_MIN}-{FORZA_MAX}) > ").strip())
        aggiungi_squadra(nome, forza)
        print(f"  Squadra '{nome}' aggiunta con forza {forza}.")
    except ValueError as e:
        print(f"  Errore: {e}")


def _azione_lista_squadre() -> None:
    squadre = carica_squadre()
    print("\n--- Squadre ---")
    if not squadre:
        print("  Nessuna squadra. Aggiungine almeno 2 per il campionato.")
        return
    for i, s in enumerate(squadre, 1):
        print(f"  {i}) {s['nome']} - forza {s['forza']}")
    print(f"  Totale: {len(squadre)}/{MAX_SQUADRE}")


def _azione_inizializza() -> None:
    print("\n--- Inizializza campionato ---")
    try:
        camp = inizializza_campionato()
        n = len(camp["calendario"])
        print(f"  Campionato creato: {len(camp['squadre'])} squadre, {n} giornate.")
    except ValueError as e:
        print(f"  Errore: {e}")


def _azione_gioca_giornata() -> None:
    stato = stato_campionato()
    if not stato.get("attivo"):
        print("  Prima inizializza un campionato.")
        return
    if stato.get("finito"):
        print("  Campionato già concluso.")
        return
    try:
        camp = carica_campionato()
        risultati = gioca_giornata(camp)
        print(f"\n  Giornata {stato['giornata'] + 1} di {stato['totale_giornate']}")
        stampa_giornata(risultati)
        stampa_classifica(camp)
    except ValueError as e:
        print(f"  Errore: {e}")


def _azione_simula_bankroll() -> None:
    """Simula l'andamento del bankroll scommettendo su ogni partita del campionato sul favorito."""
    squadre = carica_squadre()
    if len(squadre) < MIN_SQUADRE:
        print("  Aggiungi almeno 2 squadre per poter simulare.")
        return
    print("\n--- Simula bankroll sul campionato ---")
    print("  In ogni partita si scommette sull'esito con probabilità maggiore.")
    try:
        bankroll = float(input("  Bankroll iniziale [1000] > ").strip() or "1000")
        puntata = float(input("  Puntata fissa per partita [10] > ").strip() or "10")
        pc = input("  Puntata % del bankroll? (s/n) [n] > ").strip().lower() == "s"
        if pc:
            puntata = float(input("  Percentuale (0-1, es: 0.02) [0.02] > ").strip() or "0.02")
    except ValueError as e:
        print(f"  Errore: {e}")
        return
    try:
        storico = simula_bankroll_sul_campionato(
            bankroll_iniziale=bankroll,
            puntata=puntata,
            puntata_percentuale=pc,
        )
        stampa_simulazione_bankroll(storico, bankroll, max_righe=12)
    except ValueError as e:
        print(f"  Errore: {e}")


def _azione_gioca_tutte() -> None:
    stato = stato_campionato()
    if not stato.get("attivo"):
        print("  Prima inizializza un campionato.")
        return
    rimanenti = stato["totale_giornate"] - stato["giornata"]
    if rimanenti <= 0:
        print("  Campionato già concluso.")
        return
    print(f"\n  Simulo le {rimanenti} giornate rimanenti...")
    camp = carica_campionato()
    for _ in range(rimanenti):
        gioca_giornata(camp)
        camp = carica_campionato()
    print("  Campionato concluso!")
    stampa_classifica(camp)


def avvia_menu_campionato() -> None:
    """Menu loop per il campionato."""
    while True:
        scelta = _menu_campionato()
        if scelta == "1":
            _azione_aggiungi_squadra()
        elif scelta == "2":
            _azione_lista_squadre()
        elif scelta == "3":
            _azione_inizializza()
        elif scelta == "4":
            _azione_gioca_giornata()
        elif scelta == "5":
            _azione_gioca_tutte()
        elif scelta == "6":
            stampa_classifica()
        elif scelta == "7":
            _azione_simula_bankroll()
        elif scelta == "8":
            return
        else:
            print("  Scelta non valida.")
