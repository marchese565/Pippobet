"""
BetOdds Simulator - Modulo odds completo.
Comprende tutta la logica: probabilità, quote giuste, quote bookmaker, overround, prospetto.

Esecuzione:
  python odds.py          → modalità interattiva (prova quote in input)
  python odds.py --test   → esegue i unittest
"""

import sys
import unittest

TOLERANZA_PROBABILITA = 0.001


# =============================================================================
# LOGICA - Probabilità
# =============================================================================


def probabilita_valide(probabilita: list[float], tolleranza: float = TOLERANZA_PROBABILITA) -> bool:
    """Verifica che una lista di probabilità sia valida e che la somma sia 1 (±tolleranza)."""
    if not probabilita:
        raise ValueError("La lista di probabilità non può essere vuota")
    for p in probabilita:
        if p < 0 or p > 1:
            raise ValueError(f"Ogni probabilità deve essere tra 0 e 1, trovato: {p}")
    return abs(sum(probabilita) - 1.0) <= tolleranza


# =============================================================================
# LOGICA - Quote giuste
# =============================================================================


def quote_giuste(probabilita: list[float], tolleranza: float = TOLERANZA_PROBABILITA) -> list[float]:
    """Calcola le quote giuste (fair odds) a partire da una lista di probabilità.
    Formula: quota_giusta = 1 / probabilità"""
    if not probabilita_valide(probabilita, tolleranza):
        raise ValueError("Le probabilità non sono valide: la somma deve essere 1 (±tolleranza)")
    for p in probabilita:
        if p <= 0:
            raise ValueError("Ogni probabilità deve essere > 0 per calcolare la quota giusta")
    return [1.0 / p for p in probabilita]


def quota_giusta(probabilita: float) -> float:
    """Calcola la quota giusta dalla probabilità. Formula: quota_giusta = 1 / probabilita"""
    if probabilita <= 0 or probabilita > 1:
        raise ValueError("La probabilità deve essere tra 0 (escluso) e 1")
    return 1.0 / probabilita


# =============================================================================
# LOGICA - Quote bookmaker
# =============================================================================


def quota_bookmaker(quota_giusta_val: float, margine: float) -> float:
    """Applica il margine alla quota giusta. Formula: quota_bookmaker = quota_giusta × (1 - margine)"""
    if quota_giusta_val <= 0:
        raise ValueError("La quota giusta deve essere positiva")
    if margine < 0 or margine >= 1:
        raise ValueError("Il margine deve essere tra 0 (incluso) e 1 (escluso)")
    return quota_giusta_val * (1.0 - margine)


def quote_bookmaker(quote_giuste_val: list[float], margine: float) -> list[float]:
    """Applica il margine a una lista di quote giuste."""
    if not quote_giuste_val:
        raise ValueError("La lista di quote non può essere vuota")
    if margine < 0 or margine >= 1:
        raise ValueError("Il margine deve essere tra 0 (incluso) e 1 (escluso)")
    return [quota_bookmaker(q, margine) for q in quote_giuste_val]


def quote_bookmaker_da_probabilita(
    probabilita: list[float], margine: float, tolleranza: float = TOLERANZA_PROBABILITA
) -> list[float]:
    """Calcola le quote del bookmaker da probabilità e margine. Pipeline: probabilita → quote_giuste → quote_bookmaker"""
    quote_fair = quote_giuste(probabilita, tolleranza)
    return quote_bookmaker(quote_fair, margine)


# =============================================================================
# LOGICA - Probabilità implicita
# =============================================================================


def probabilita_implicita(quota: float) -> float:
    """Calcola la probabilità implicita da una quota. Formula: probabilita = 1 / quota"""
    if quota <= 0:
        raise ValueError("La quota deve essere positiva")
    return 1.0 / quota


# =============================================================================
# LOGICA - Vincita e profitto
# =============================================================================


def calcola_vincita(puntata: float, quota: float) -> float:
    """Calcola la vincita totale per una scommessa vincente. Vincita = puntata × quota"""
    if puntata < 0:
        raise ValueError("La puntata non può essere negativa")
    if quota <= 0:
        raise ValueError("La quota deve essere positiva")
    return puntata * quota


def calcola_profitto(puntata: float, quota: float, vinto: bool) -> float:
    """Calcola il profitto (o perdita) di una scommessa."""
    return calcola_vincita(puntata, quota) - puntata if vinto else -puntata


# =============================================================================
# LOGICA - Overround
# =============================================================================


def calcola_overround(quote: list[float]) -> float:
    """Calcola l'overround dato da un set di quote del bookmaker. Formula: sum(1/quota_i) - 1"""
    if not quote:
        raise ValueError("Serve almeno una quota")
    return sum(1.0 / q for q in quote if q > 0) - 1.0


def margine_totale(quote: list[float]) -> float:
    """Calcola il margine totale (overround) di un mercato a quote multiple."""
    return calcola_overround(quote)


# =============================================================================
# LOGICA - Prospetto formattato
# =============================================================================


def stampa_prospetto_quote(
    probabilita: list[float],
    margine: float = 0.05,
    tolleranza: float = TOLERANZA_PROBABILITA,
) -> None:
    """Stampa un prospetto quote formattato con probabilità, quote giuste e quote bookmaker."""
    quote_fair = quote_giuste(probabilita, tolleranza)
    quote_book = quote_bookmaker_da_probabilita(probabilita, margine, tolleranza)
    overround = calcola_overround(quote_book)

    larghezza = 12
    sep = "+" + "-" * (larghezza + 2) * 4 + "+"
    riga = "| {:>" + str(larghezza) + "} | {:>" + str(larghezza) + "} | {:>" + str(larghezza) + "} | {:>" + str(larghezza) + "} |"

    print("\n" + sep)
    print(riga.format("Esito", "Prob", "Quota giusta", "Quota book"))
    print(sep)

    for i, (p, qf, qb) in enumerate(zip(probabilita, quote_fair, quote_book), 1):
        print(riga.format(str(i), f"{p:.2%}", f"{qf:.4f}", f"{qb:.4f}"))

    print(sep)
    print(f"  Margine: {margine:.1%}  |  Overround: {overround:.2%}\n")


# =============================================================================
# MODALITÀ INTERATTIVA
# =============================================================================


def _modalita_interattiva() -> None:
    """Permette di inserire probabilità manualmente per provare le funzioni."""
    print("\n--- BetOdds Simulator - Prova quote in input ---")
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


# =============================================================================
# UNITTEST
# =============================================================================


class TestProbabilitaValide(unittest.TestCase):
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
    def test_formula_quota_giusta(self):
        prob = 0.6
        result = quote_giuste([prob, 0.25, 0.15])[0]
        self.assertAlmostEqual(result, quota_giusta(prob), places=6)

    def test_due_esiti_50_50(self):
        probs = [0.5, 0.5]
        result = quote_giuste(probs)
        expected = [quota_giusta(p) for p in probs]
        assert result == expected

    def test_esito_certo(self):
        result = quote_giuste([1.0])[0]
        assert result == quota_giusta(1.0)

    def test_somma_non_valida_solleva_errore(self):
        with self.assertRaises(ValueError):
            quote_giuste([0.70, 0.25, 0.15])

    def test_probabilita_zero_solleva_errore(self):
        with self.assertRaises(ValueError):
            quote_giuste([0.5, 0.5, 0.0])


class TestQuotaGiusta(unittest.TestCase):
    def test_formula_1_div_probabilita(self):
        prob = 0.6
        result = quota_giusta(prob)
        assert result == 1.0 / prob

    def test_probabilita_05(self):
        assert quota_giusta(0.5) == 1.0 / 0.5


class TestQuoteBookmaker(unittest.TestCase):
    def test_formula_quota_giusta_per_margine(self):
        quote_fair = quote_giuste([0.5, 0.5])
        margine = 0.05
        result = quote_bookmaker(quote_fair, margine)
        for i, q in enumerate(quote_fair):
            expected = quota_bookmaker(q, margine)
            self.assertAlmostEqual(result[i], expected, places=6)

    def test_prob_05_con_margine_05_diventa_quote_ridotta(self):
        result = quote_bookmaker_da_probabilita([0.5, 0.5], 0.05)
        expected = quota_bookmaker(quota_giusta(0.5), 0.05)
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
    def test_formula_quota_giusta_per_margine(self):
        q_fair = quota_giusta(0.5)
        margine = 0.05
        result = quota_bookmaker(q_fair, margine)
        assert result == q_fair * (1 - margine)


class TestProbabilitaImplicita(unittest.TestCase):
    def test_inversa_quota_giusta(self):
        q = quota_giusta(0.5)
        assert probabilita_implicita(q) == 0.5

    def test_quota_invalida(self):
        with self.assertRaises(ValueError):
            probabilita_implicita(-1)


class TestCalcolaVincita(unittest.TestCase):
    def test_puntata_per_quota(self):
        puntata, quota = 10, quota_giusta(0.5)
        assert calcola_vincita(puntata, quota) == puntata * quota


class TestCalcolaProfitto(unittest.TestCase):
    def test_vinto(self):
        puntata, quota = 10, quota_giusta(0.5)
        assert calcola_profitto(puntata, quota, True) == calcola_vincita(puntata, quota) - puntata

    def test_perso(self):
        assert calcola_profitto(10, quota_giusta(0.5), False) == -10


class TestCalcolaOverround(unittest.TestCase):
    def test_quote_fair_overround_zero(self):
        assert calcola_overround(quote_giuste([0.5, 0.5])) == 0.0

    def test_quote_bookmaker_ha_overround(self):
        result = calcola_overround(quote_bookmaker_da_probabilita([0.5, 0.5], 0.05))
        self.assertGreater(result, 0)

    def test_lista_vuota_solleva_errore(self):
        with self.assertRaises(ValueError):
            calcola_overround([])

    def test_margine_totale_uguale_calcola_overround(self):
        quote = quote_bookmaker_da_probabilita([0.6, 0.25, 0.15], 0.05)
        assert margine_totale(quote) == calcola_overround(quote)


class TestMargineTotale(unittest.TestCase):
    def test_usa_calcola_overround(self):
        quote = quote_bookmaker_da_probabilita([0.5, 0.5], 0.05)
        assert margine_totale(quote) == calcola_overround(quote)


class TestStampaProspettoQuote(unittest.TestCase):
    def test_stampa_non_solleva_errore(self):
        stampa_prospetto_quote([0.5, 0.5], margine=0.05)

    def test_usa_quote_giuste_e_bookmaker(self):
        stampa_prospetto_quote([0.6, 0.25, 0.15], margine=0.05)


# =============================================================================
# ENTRY POINT
# =============================================================================


if __name__ == "__main__":
    if "--test" in sys.argv or "-t" in sys.argv:
        sys.argv = [sys.argv[0]] + [a for a in sys.argv[1:] if a not in ("--test", "-t")]
        unittest.main()
    else:
        _modalita_interattiva()
