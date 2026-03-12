"""
BetOdds Simulator - Modulo client.
Gestisce gli input dall'utente da terminale.

Questo modulo lavora insieme a odds.py:
  - client.py: input/output utente
  - odds.py: logica matematica
"""

from odds import (
    probabilita_valide,
    quote_giuste,
    quote_bookmaker_da_probabilita,
    stampa_prospetto_quote,
)
from storage import carica_cronologia, aggiungi_partita


MARGINE_MIN = 0.01
MARGINE_MAX = 0.20


def leggi_probabilita(prompt: str = "Probabilità > ") -> list[float] | None:
    """
    Legge una lista di probabilità da terminale.
    Validazione: ogni valore tra 0 e 1, somma = 1.0.
    """
    inp = input(prompt).strip()
    if inp.lower() == "q":
        return None

    parti = [p.strip() for p in inp.split(",")]
    try:
        probabilita = [float(p) for p in parti]
    except ValueError:
        raise ValueError("Inserisci numeri separati da virgola.")

    for p in probabilita:
        if p < 0 or p > 1:
            raise ValueError(f"Ogni probabilità deve essere tra 0 e 1. Trovato: {p}")

    if len(probabilita) == 1 and probabilita[0] < 1:
        probabilita = [probabilita[0], 1 - probabilita[0]]

    if abs(sum(probabilita) - 1.0) > 0.001:
        raise ValueError(f"La somma delle probabilità deve essere 1.0. Somma attuale: {sum(probabilita):.4f}")

    return probabilita


def leggi_margine(
    prompt: str = f"Margine (1%-20%, es: 5 o 0.05) [invio=5%] > ",
    default: float = 0.05,
    min_m: float = MARGINE_MIN,
    max_m: float = MARGINE_MAX,
) -> float:
    """
    Legge il margine da terminale.

    Args:
        prompt: Messaggio da mostrare
        default: Valore se l'utente preme invio

    Returns:
        Margine come float (es. 0.05)
    """
    inp = input(prompt).strip()
    if not inp:
        if min_m <= default <= max_m:
            return default
        return min_m

    m = float(inp)
    if m > 1:
        m = m / 100

    if m < min_m or m > max_m:
        raise ValueError(f"Il margine deve essere tra {min_m*100:.0f}% e {max_m*100:.0f}%. Inserito: {m*100:.1f}%")

    return m


def stampa_messaggio(msg: str) -> None:
    """Stampa un messaggio all'utente."""
    print(msg)


def stampa_errore(msg: str) -> None:
    """Stampa un messaggio di errore chiaro."""
    print(f"  ⚠ {msg}")
    print("  Riprova.\n")


def _menu_principale() -> str:
    """Mostra il menu e restituisce la scelta dell'utente."""
    print("\n--- BetOdds Simulator ---")
    print("  1) Calcolo quote")
    print("  2) Simula scommessa")
    print("  3) Cronologia")
    print("  4) Esci")
    return input("Scelta > ").strip()


def _azione_calcolo_quote() -> None:
    """Esegue il calcolo delle quote da probabilità."""
    print("\n" + "=" * 40)
    print("  CALCOLO QUOTE")
    print("=" * 40)
    print("\n  Prob separate da virgola. Somma = 1. Margine 1%-20%.")
    print("  'q' per tornare.\n")

    while True:
        try:
            probabilita = leggi_probabilita("  Probabilità > ")
            if probabilita is None:
                return
            print(f"  ✓ Ok: {probabilita}  |  Somma: {sum(probabilita):.2f}\n")
            break
        except ValueError as e:
            stampa_errore(str(e))

    while True:
        try:
            margine = leggi_margine("  Margine % (1-20, invio=5) > ")
            print(f"  ✓ Margine: {margine*100:.0f}%\n")
            break
        except ValueError as e:
            stampa_errore(str(e))

    stampa_prospetto_quote(probabilita, margine=margine)


def _azione_simula_scommessa() -> None:
    """Simula una scommessa con input guidato: partita, esiti (1,X,2), probabilità."""
    print("\n" + "=" * 40)
    print("  SIMULA SCOMMESSA")
    print("=" * 40)
    print("\n  Inserisci i dati. 'q' per tornare.\n")

    nome = input("  Nome partita (es: Juventus - Torino)\n  > ").strip()
    if nome.lower() == "q":
        return

    esiti = ["1", "X", "2"]
    labels = {"1": "1", "X": "X", "2": "2"}
    print("\n  Esiti:  1 = sinistra | X = pareggio | 2 = destra")
    print("  Regole: prob 0-1, somma = 1. Margine 1%-20%.\n")

    probabilita = []
    for esito in esiti:
        label = labels[esito]
        while True:
            inp = input(f"  Prob {label} > ").strip()
            if inp.lower() == "q":
                return
            try:
                p = float(inp)
                if 0 <= p <= 1:
                    probabilita.append(p)
                    break
                    stampa_errore(f"Valore {p} non valido. Deve essere tra 0 e 1.")
            except ValueError:
                stampa_errore("Inserisci un numero (es: 0.45).")

    while not probabilita_valide(probabilita):
        stampa_errore(f"Somma = {sum(probabilita):.2f}. Deve essere 1.0. Reinserisci.\n")
        probabilita = []
        for esito in esiti:
            label = labels[esito]
            while True:
                inp = input(f"  Prob {label} > ").strip()
                if inp.lower() == "q":
                    return
                try:
                    p = float(inp)
                    if 0 <= p <= 1:
                        probabilita.append(p)
                        break
                    stampa_errore(f"Valore {p} non valido. Deve essere tra 0 e 1.")
                except ValueError:
                    stampa_errore("Inserisci un numero (es: 0.45).")

    print()
    while True:
        try:
            margine = leggi_margine("  Margine % (1-20, invio=5) > ")
            print(f"  ✓ Margine: {margine*100:.0f}%\n")
            break
        except ValueError as e:
            stampa_errore(str(e))

    try:
        quote_fair = quote_giuste(probabilita)
        quote_book = quote_bookmaker_da_probabilita(probabilita, margine)

        print(f"\n--- {nome} ---")
        stampa_prospetto_quote(probabilita, margine=margine, esiti=esiti)

        partita = {
            "nome": nome,
            "esiti": esiti,
            "probabilita": probabilita,
            "quote_giuste": quote_fair,
            "quote_book": quote_book,
            "margine": margine,
        }
        cronologia = carica_cronologia()
        aggiungi_partita(cronologia, partita)
        print("  Partita salvata in cronologia.")
    except ValueError as e:
        stampa_errore(str(e))


def _azione_cronologia() -> None:
    """Mostra la cronologia delle partite salvate con le rispettive quote."""
    print("\n--- Cronologia ---")
    cronologia = carica_cronologia()
    if not cronologia:
        print("  Nessuna partita salvata.")
        return
    for i, p in enumerate(cronologia, 1):
        print(f"\n  {i}) {p['nome']}")
        for esito, prob, qg, qb in zip(p["esiti"], p["probabilita"], p["quote_giuste"], p["quote_book"]):
            print(f"     {esito}: prob {prob:.2%} | quota giusta {qg:.2f} | quota book {qb:.2f}")


def avvia_menu() -> None:
    """Avvia il menu principale in loop."""
    while True:
        scelta = _menu_principale()
        if scelta == "1":
            _azione_calcolo_quote()
        elif scelta == "2":
            _azione_simula_scommessa()
        elif scelta == "3":
            _azione_cronologia()
        elif scelta == "4":
            print("\nUscita. Arrivederci!")
            break
        else:
            stampa_errore("Scelta non valida. Inserisci 1, 2, 3 o 4.")


if __name__ == "__main__":
    avvia_menu()
