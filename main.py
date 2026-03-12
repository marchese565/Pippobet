"""
BetOdds Simulator - Entry point principale del progetto.

Avvia l'applicazione completa. Esecuzione:
python py

Moduli del progetto:
  - client.py      : menu principale (calcolo quote, scommesse, cronologia)
  - simulator.py   : simulatore scommesse casuali con andamento bankroll
  - campionato.py  : campionato con squadre, forze, quote dinamiche, classifica
  - campionato_ui.py: interfaccia campionato
  - odds.py       : logica quote, probabilità, overround
  - storage.py    : persistenza cronologia, session, squadre
"""

import sys


def _menu_avvio() -> str:
    """Menu di avvio per scegliere quale modulo eseguire."""
    print("\n" + "=" * 45)
    print("  BETODDS SIMULATOR")
    print("=" * 45)
    print("  1) Menu principale (calcolo quote, scommesse, cronologia)")
    print("  2) Simulatore scommesse casuali")
    print("  3) Campionato (squadre, classifica, 38 giornate)")
    print("  4) Sito web scommesse")
    print("  5) Esci")
    print()
    return input("Scelta > ").strip()


def main() -> None:
    """Avvia il progetto BetOdds Simulator."""
    while True:
        scelta = _menu_avvio()
        if scelta == "1":
            from client import avvia_menu
            avvia_menu()
        elif scelta == "2":
            from simulator import _modalita_interattiva
            _modalita_interattiva()
        elif scelta == "3":
            from campionato_ui import avvia_menu_campionato
            avvia_menu_campionato()
        elif scelta == "4":
            from app import main as avvia_web
            avvia_web()
        elif scelta == "5":
            print("\nUscita. Arrivederci!")
            sys.exit(0)
        else:
            print("  Scelta non valida. Inserisci 1, 2, 3, 4 o 5.")


if __name__ == "__main__":
    main()
