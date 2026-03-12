"""
Test per il modulo odds.py
Usa unittest con assert e metodi self.assert*

Esecuzione:
  python test_odds.py          → modalità interattiva (inserisci probabilità)
  python test_odds.py --test   → esegue i unittest
"""

import sys
import unittest
from odds import (
    probabilita_valide,
    quote_giuste,
    quote_bookmaker,
    quote_bookmaker_da_probabilita,
    calcola_overround,
    quota_giusta,
    quota_bookmaker,
    stampa_prospetto_quote,
    probabilita_implicita,
    calcola_vincita,
    calcola_profitto,
    margine_totale,
)


class TestProbabilitaValide(unittest.TestCase):
    """Test per la funzione probabilita_valide."""

    def test_lista_valida_esatta(self):
        self.assertTrue(probabilita_valide([0.60, 0.25, 0.15]))

    def test_lista_valida_con_tolleranza(self):
        self.assertTrue(probabilita_valide([0.60, 0.25, 0.151]))

    def test_lista_non_valida_somma_troppo_alta(self):
        self.assertFalse(probabilita_valide([0.70, 0.25, 0.15]))

    def test_lista_non_valida_somma_troppo_bassa(self):
        self.assertFalse(probabilita_valide([0.50, 0.25, 0.15]))

    def test_lista_vuota_solleva_errore(self):
        with self.assertRaises(ValueError):
            probabilita_valide([])


class TestQuoteGiuste(unittest.TestCase):
    """Test per la funzione quote_giuste."""

    def test_formula_quota_giusta(self):
        """Formula: quota_giusta = 1 / probabilità."""
        prob = 0.6
        result = quote_giuste([prob, 0.25, 0.15])[0]
        self.assertAlmostEqual(result, quota_giusta(prob), places=6)

    def test_due_esiti_50_50(self):
        """Somma prob=1 → quote da formula 1/p."""
        probs = [0.5, 0.5]
        result = quote_giuste(probs)
        expected = [quota_giusta(p) for p in probs]
        assert result == expected

    def test_esito_certo(self):
        """Prob 1 → quota 1."""
        result = quote_giuste([1.0])[0]
        assert result == quota_giusta(1.0)

    def test_somma_non_valida_solleva_errore(self):
        with self.assertRaises(ValueError):
            quote_giuste([0.70, 0.25, 0.15])

    def test_probabilita_zero_solleva_errore(self):
        with self.assertRaises(ValueError):
            quote_giuste([0.5, 0.5, 0.0])


class TestQuotaGiusta(unittest.TestCase):
    """Test per la funzione quota_giusta."""

    def test_formula_1_div_probabilita(self):
        """Formula: quota_giusta = 1 / probabilità."""
        prob = 0.6
        result = quota_giusta(prob)
        assert result == 1.0 / prob

    def test_probabilita_05(self):
        result = quota_giusta(0.5)
        assert result == 1.0 / 0.5


class TestQuoteBookmaker(unittest.TestCase):
    """Test per la funzione quote_bookmaker (lista di quote)."""

    def test_formula_quota_giusta_per_margine(self):
        """Formula: quota_bookmaker = quota_giusta × (1 - margine)."""
        quote_fair = quote_giuste([0.5, 0.5])
        margine = 0.05
        result = quote_bookmaker(quote_fair, margine)
        for i, q in enumerate(quote_fair):
            expected = quota_bookmaker(q, margine)
            self.assertAlmostEqual(result[i], expected, places=6)

    def test_prob_05_con_margine_05_diventa_quote_ridotta(self):
        """Prob 0.5 → quota giusta 2 → con margine → quota < 2."""
        result = quote_bookmaker_da_probabilita([0.5, 0.5], 0.05)
        q_fair = quota_giusta(0.5)
        expected = quota_bookmaker(q_fair, 0.05)
        assert result[0] == expected

    def test_margine_zero_lascia_invariato(self):
        quote_fair = quote_giuste([0.5, 0.5])
        result = quote_bookmaker(quote_fair, 0)
        assert result == quote_fair

    def test_lista_vuota_solleva_errore(self):
        with self.assertRaises(ValueError):
            quote_bookmaker([], 0.05)

    def test_margine_invalido_solleva_errore(self):
        with self.assertRaises(ValueError):
            quote_bookmaker(quote_giuste([0.5, 0.5]), 1.0)


class TestQuotaBookmakerSingola(unittest.TestCase):
    """Test per quota_bookmaker (singola quota)."""

    def test_formula_quota_giusta_per_margine(self):
        """Formula: quota_bookmaker = quota_giusta × (1 - margine)."""
        q_fair = quota_giusta(0.5)
        margine = 0.05
        result = quota_bookmaker(q_fair, margine)
        expected = q_fair * (1 - margine)
        assert result == expected


class TestProbabilitaImplicita(unittest.TestCase):
    """Test per probabilita_implicita."""

    def test_inversa_quota_giusta(self):
        """Prob implicita = 1/quota, inversa di quota_giusta."""
        q = quota_giusta(0.5)
        assert probabilita_implicita(q) == 0.5

    def test_quota_invalida(self):
        with self.assertRaises(ValueError):
            probabilita_implicita(-1)


class TestCalcolaVincita(unittest.TestCase):
    """Test per calcola_vincita."""

    def test_puntata_per_quota(self):
        """Vincita = puntata × quota."""
        puntata = 10
        quota = quota_giusta(0.5)
        assert calcola_vincita(puntata, quota) == puntata * quota


class TestCalcolaProfitto(unittest.TestCase):
    """Test per calcola_profitto."""

    def test_vinto(self):
        puntata, quota = 10, quota_giusta(0.5)
        assert calcola_profitto(puntata, quota, True) == calcola_vincita(puntata, quota) - puntata

    def test_perso(self):
        puntata = 10
        assert calcola_profitto(puntata, quota_giusta(0.5), False) == -puntata


class TestCalcolaOverround(unittest.TestCase):
    """Test per calcola_overround."""

    def test_quote_fair_overround_zero(self):
        """Quote giuste → overround 0."""
        quote_fair = quote_giuste([0.5, 0.5])
        assert calcola_overround(quote_fair) == 0.0

    def test_quote_bookmaker_ha_overround(self):
        """Quote bookmaker → overround > 0."""
        quote_book = quote_bookmaker_da_probabilita([0.5, 0.5], 0.05)
        result = calcola_overround(quote_book)
        self.assertGreater(result, 0)

    def test_lista_vuota_solleva_errore(self):
        with self.assertRaises(ValueError):
            calcola_overround([])

    def test_margine_totale_uguale_calcola_overround(self):
        """margine_totale usa calcola_overround."""
        quote = quote_bookmaker_da_probabilita([0.6, 0.25, 0.15], 0.05)
        assert margine_totale(quote) == calcola_overround(quote)


class TestMargineTotale(unittest.TestCase):
    """Test per margine_totale."""

    def test_usa_calcola_overround(self):
        quote = quote_bookmaker_da_probabilita([0.5, 0.5], 0.05)
        assert margine_totale(quote) == calcola_overround(quote)


class TestStampaProspettoQuote(unittest.TestCase):
    """Test per stampa_prospetto_quote."""

    def test_stampa_non_solleva_errore(self):
        """Chiamata con probabilità valide non solleva eccezioni."""
        stampa_prospetto_quote([0.5, 0.5], margine=0.05)

    def test_usa_quote_giuste_e_bookmaker(self):
        """Il prospetto usa quote_giuste e quote_bookmaker_da_probabilita."""
        prob = [0.6, 0.25, 0.15]
        stampa_prospetto_quote(prob, margine=0.05)


def _modalita_interattiva() -> None:
    """Permette di inserire probabilità manualmente per testare le funzioni."""
    print("\n--- Modalità interattiva - Test funzioni odds ---")
    print("Inserisci le probabilità separate da virgola (es: 0.60, 0.25, 0.15)")
    print("Oppure 'q' per uscire\n")

    while True:
        try:
            inp = input("Probabilità > ").strip()
            if inp.lower() == "q":
                print("Uscita.")
                break

            parti = [p.strip() for p in inp.split(",")]
            probabilita = [float(p) for p in parti]
            if len(probabilita) == 1 and probabilita[0] < 1:
                probabilita = [probabilita[0], 1 - probabilita[0]]
                print(f"  Input normalizzato (evento binario): {probabilita}")
            else:
                print(f"  Input: {probabilita}")
            print(f"  Somma: {sum(probabilita):.4f}")

            try:
                valide = probabilita_valide(probabilita)
                print(f"  probabilita_valide(): {valide}")
            except ValueError as e:
                print(f"  probabilita_valide(): ValueError - {e}")

            try:
                stampa_prospetto_quote(probabilita, margine=0.05)
            except ValueError as e:
                print(f"  Errore: {e}")

        except (ValueError, KeyboardInterrupt) as e:
            if isinstance(e, KeyboardInterrupt):
                print("\nUscita.")
                break
            print(f"  Errore: {e}")
        print()


if __name__ == "__main__":
    # Modalità interattiva di default; usa --test o -t per i unittest
    if "--test" in sys.argv or "-t" in sys.argv:
        unittest.main()
    else:
        _modalita_interattiva()
