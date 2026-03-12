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
    quote_doppie_da_probabilita,
    simula_esito,
    scommessa_vincente,
    calcola_vincita,
    stampa_prospetto_quote,
)
from storage import (
    carica_cronologia,
    aggiungi_partita,
    aggiungi_evento_sessione,
    carica_sessione,
    elimina_cronologia,
    esporta_cronologia_csv,
)


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
    print("  4) Elimina cronologia")
    print("  5) Esporta cronologia in CSV")
    print("  6) Esci")
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

    quote_fair = quote_giuste(probabilita)
    quote_book = quote_bookmaker_da_probabilita(probabilita, margine)
    stampa_prospetto_quote(probabilita, margine=margine)
    if len(probabilita) == 3:
        quote_doppie = quote_doppie_da_probabilita(probabilita, margine)
        print("  Quote doppie:  1X = {:.2f}  |  X2 = {:.2f}  |  12 = {:.2f}\n".format(
            quote_doppie["1X"], quote_doppie["X2"], quote_doppie["12"]))
    aggiungi_evento_sessione("calcolo_quote", {
        "probabilita": probabilita,
        "margine": margine,
        "quote_giuste": quote_fair,
        "quote_book": quote_book,
    })


def _azione_simula_scommessa() -> None:
    """Simula una scommessa con input guidato: partita, esiti (1,X,2), probabilità, opzione scommessa."""
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
        quote_doppie = quote_doppie_da_probabilita(probabilita, margine)

        print(f"\n--- {nome} ---")
        stampa_prospetto_quote(probabilita, margine=margine, esiti=esiti)
        print("  Quote doppie chance:  1X = {:.2f}  |  X2 = {:.2f}  |  12 = {:.2f}".format(
            quote_doppie["1X"], quote_doppie["X2"], quote_doppie["12"]))

        partita = {
            "nome": nome,
            "esiti": esiti,
            "probabilita": probabilita,
            "quote_giuste": quote_fair,
            "quote_book": quote_book,
            "quote_doppie": quote_doppie,
            "margine": margine,
        }

        # Opzione scommessa
        scommetti = input("\n  Vuoi scommettere su questa partita? (s/n) [n] > ").strip().lower()
        if scommetti == "s":
            tipi = [("1", quote_book[0]), ("X", quote_book[1]), ("2", quote_book[2]),
                    ("1X", quote_doppie["1X"]), ("X2", quote_doppie["X2"]), ("12", quote_doppie["12"])]
            print("\n  Scegli la scommessa:")
            for i, (tipo, quota) in enumerate(tipi, 1):
                print(f"    {i}) {tipo} @ {quota:.2f}")
            print("    0) Annulla")

            while True:
                scelta = input("  Scelta (1-6) > ").strip()
                if scelta == "0" or scelta.lower() == "q":
                    print("  Scommessa annullata.")
                    break
                try:
                    idx = int(scelta)
                    if 1 <= idx <= 6:
                        tipo_scelto, quota_scelta = tipi[idx - 1]
                        break
                    stampa_errore("Inserisci un numero da 1 a 6.")
                except ValueError:
                    stampa_errore("Inserisci un numero da 1 a 6.")

            if scelta != "0" and scelta.lower() != "q":
                while True:
                    inp_puntata = input(f"  Puntata (€) su {tipo_scelto} @ {quota_scelta:.2f} > ").strip()
                    if inp_puntata.lower() == "q":
                        print("  Scommessa annullata.")
                        break
                    try:
                        puntata = float(inp_puntata)
                        if puntata > 0:
                            break
                        stampa_errore("La puntata deve essere positiva.")
                    except ValueError:
                        stampa_errore("Inserisci un importo valido (es: 10).")

                if inp_puntata.lower() != "q":
                    esito_simulato = simula_esito(probabilita)
                    esito_label = esiti[esito_simulato]
                    vinto = scommessa_vincente(tipo_scelto, esito_simulato)
                    vincita = calcola_vincita(puntata, quota_scelta) if vinto else 0.0

                    partita["scommessa"] = {
                        "tipo": tipo_scelto,
                        "quota": quota_scelta,
                        "puntata": puntata,
                        "esito_partita": esito_label,
                        "vinto": vinto,
                        "vincita": vincita,
                    }

                    print(f"\n  --- Risultato simulato: {esito_label} ---")
                    print(f"  La partita è finita {esito_label}.", end=" ")
                    if vinto:
                        print(f"Hai vinto! Vincita: €{vincita:,.2f}")
                    else:
                        print(f"Scommessa persa. Perdita: €{puntata:,.2f}")

        cronologia = carica_cronologia()
        aggiungi_partita(cronologia, partita)
        aggiungi_evento_sessione("simula_scommessa", partita)
        print("  Partita salvata in cronologia.")
    except ValueError as e:
        stampa_errore(str(e))


def _formatta_data_ora(ts: str) -> tuple[str, str]:
    """Estrae data e ora dal timestamp ISO."""
    try:
        # formato: 2026-03-05T02:35:49.008120
        dt = ts.split("T")
        data = dt[0] if len(dt) > 0 else ts
        ora = dt[1][:8] if len(dt) > 1 and len(dt[1]) >= 8 else ""
        return (data, ora)
    except (IndexError, AttributeError):
        return (ts, "")


def _azione_cronologia() -> None:
    """Mostra la cronologia degli eventi: data, ora, evento, quote, risultato simulazione."""
    print("\n--- Cronologia ---")
    sessione = carica_sessione()
    if not sessione:
        print("  Nessun evento salvato.")
        return

    for i, ev in enumerate(reversed(sessione), 1):
        ts = ev.get("timestamp", "")
        data, ora = _formatta_data_ora(ts)
        tipo = ev.get("tipo", "?")

        if tipo == "calcolo_quote":
            evento_nome = "Calcolo quote"
            quote = ev.get("quote_book", ev.get("quote_giuste", []))
            quote_str = ", ".join(f"{q:.2f}" for q in quote) if quote else "-"
            risultato = f"Quote book: {quote_str}"
        elif tipo == "simula_scommessa":
            evento_nome = ev.get("nome", "Simula scommessa")
            quote = ev.get("quote_book", [])
            quote_str = ", ".join(f"{q:.2f}" for q in quote) if quote else "-"
            scommessa = ev.get("scommessa", {})
            if scommessa:
                esito_p = scommessa.get("esito_partita", "?")
                vinto = scommessa.get("vinto", False)
                vincita = scommessa.get("vincita", 0)
                risultato = f"Quote: {quote_str} | Scommessa {scommessa.get('tipo','')} | Esito: {esito_p} | {'VINTO €' + f'{vincita:,.2f}' if vinto else 'PERSO'}"
            else:
                risultato = f"Quote: {quote_str}"
        elif tipo == "campionato_inizializzato":
            evento_nome = "Campionato inizializzato"
            quote_str = "-"
            risultato = f"{ev.get('squadre', 0)} squadre, {ev.get('giornate', 0)} giornate"
        elif tipo == "simulazione_bankroll_campionato":
            evento_nome = "Simulazione bankroll campionato"
            quote_str = "-"
            bf = ev.get("bankroll_finale", 0)
            v = ev.get("vittorie", 0)
            p = ev.get("partite", 0)
            risultato = f"Bankroll finale: {bf:,.0f} | Vittorie: {v}/{p}"
        elif tipo == "partita_campionato":
            evento_nome = ev.get("partita", "Partita campionato")
            quote = ev.get("quote", [])
            quote_str = ", ".join(f"{q:.2f}" for q in quote) if quote else "-"
            risultato = f"Esito: {ev.get('esito', '?')}"
        elif tipo == "simulazione":
            evento_nome = "Simulazione scommesse"
            bankroll_f = ev.get("bankroll_finale", 0)
            vittorie = ev.get("vittorie", 0)
            totali = ev.get("totali", 0)
            variaz = ev.get("variazione_pct", 0)
            quota_min = ev.get("quota_min", 0)
            quota_max = ev.get("quota_max", 0)
            quote_str = f"{quota_min:.2f}-{quota_max:.2f}" if quota_min or quota_max else "-"
            risultato = f"Bankroll finale: {bankroll_f:,.0f} | Vittorie: {vittorie}/{totali} | Variaz: {variaz:+.1f}%"
        else:
            evento_nome = tipo
            quote_str = "-"
            risultato = ""

        print(f"\n  {i}) {data}  {ora}  |  {evento_nome}")
        print(f"     Quote: {quote_str}")
        print(f"     Risultato: {risultato}")


def _azione_elimina_cronologia() -> None:
    """Elimina cronologia e sessione dopo conferma."""
    print("\n--- Elimina cronologia ---")
    risposta = input("  Eliminare tutta la cronologia? (s/n) [n] > ").strip().lower()
    if risposta == "s":
        elimina_cronologia()
        print("  Cronologia eliminata.")
    else:
        print("  Operazione annullata.")


def _azione_esporta_csv() -> None:
    """Esporta la cronologia in un file CSV leggibile con Excel."""
    print("\n--- Esporta cronologia in CSV ---")
    if not carica_sessione():
        print("  Nessun evento da esportare.")
        return
    try:
        path = esporta_cronologia_csv()
        print(f"  File salvato: {path}")
        print("  Apri con Excel (codifica UTF-8, separatore punto e virgola).")
    except OSError as e:
        stampa_errore(f"Impossibile scrivere il file: {e}")


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
            _azione_elimina_cronologia()
        elif scelta == "5":
            _azione_esporta_csv()
        elif scelta == "6":
            print("\nUscita. Arrivederci!")
            break
        else:
            stampa_errore("Scelta non valida. Inserisci 1, 2, 3, 4, 5 o 6.")


if __name__ == "__main__":
    avvia_menu()
