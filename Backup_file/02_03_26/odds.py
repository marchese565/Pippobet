"""
Modulo odds.py - Logica matematica del BetOdds Simulator.

Gestisce:
- Quota (Odd): moltiplicatore della vincita
- Quota giusta (Fair Odd): quota senza margine del bookmaker
- Overround (Margine): margine applicato alle quote
"""

TOLERANZA_PROBABILITA = 0.001


def probabilita_valide(probabilita: list[float], tolleranza: float = TOLERANZA_PROBABILITA) -> bool:
    """
    Verifica che una lista di probabilità sia valida e che la somma sia 1 (±tolleranza).

    Args:
        probabilita: Lista di probabilità
        tolleranza: Tolleranza sulla somma (default 0.001)

    Returns:
        True se la somma è tra 1 - tolleranza e 1 + tolleranza

    Raises:
        ValueError: Se la lista è vuota o contiene valori non validi (0 <= p <= 1)
    """
    if not probabilita:
        raise ValueError("La lista di probabilità non può essere vuota")

    for p in probabilita:
        if p < 0 or p > 1:
            raise ValueError(f"Ogni probabilità deve essere tra 0 e 1, trovato: {p}")

    somma = sum(probabilita)
    return abs(somma - 1.0) <= tolleranza


def quote_giuste(probabilita: list[float], tolleranza: float = TOLERANZA_PROBABILITA) -> list[float]:
    """
    Calcola le quote giuste (fair odds) a partire da una lista di probabilità.

    Formula per ogni esito: quota_giusta = 1 / probabilità

    Args:
        probabilita: Lista di probabilità che deve sommare a 1 (±tolleranza)
        tolleranza: Tolleranza sulla somma delle probabilità (default 0.001)

    Returns:
        Lista di quote giuste corrispondenti alle probabilità

    Raises:
        ValueError: Se le probabilità non sono valide o la somma non è 1
    """
    if not probabilita_valide(probabilita, tolleranza):
        raise ValueError(
            "Le probabilità non sono valide: la somma deve essere 1 (±tolleranza)"
        )
    for p in probabilita:
        if p <= 0:
            raise ValueError(
                "Ogni probabilità deve essere > 0 per calcolare la quota giusta"
            )
    return [1.0 / p for p in probabilita]


def quota_giusta(probabilita: float) -> float:
    """
    Calcola la quota giusta (fair odd) dalla probabilità.

    Formula: quota_giusta = 1 / probabilita

    Args:
        probabilita: Probabilità dell'evento (0 < p <= 1)

    Returns:
        La quota giusta corrispondente

    Raises:
        ValueError: Se la probabilità non è valida
    """
    if probabilita <= 0 or probabilita > 1:
        raise ValueError("La probabilità deve essere tra 0 (escluso) e 1")
    return 1.0 / probabilita


def quota_bookmaker(quota_giusta_val: float, margine: float) -> float:
    """
    Applica il margine (overround) alla quota giusta per ottenere la quota del bookmaker.

    Formula: quota_bookmaker = quota_giusta × (1 - margine)

    Args:
        quota_giusta_val: Quota senza margine (quota giusta)
        margine: Overround in percentuale (es. 0.05 per 5%)

    Returns:
        La quota del bookmaker

    Raises:
        ValueError: Se i valori non sono validi
    """
    if quota_giusta_val <= 0:
        raise ValueError("La quota giusta deve essere positiva")
    if margine < 0 or margine >= 1:
        raise ValueError("Il margine deve essere tra 0 (incluso) e 1 (escluso)")
    # quota_bookmaker = quota_giusta × (1 - margine)
    return quota_giusta_val * (1.0 - margine)


def quote_bookmaker_da_probabilita(
    probabilita: list[float], margine: float, tolleranza: float = TOLERANZA_PROBABILITA
) -> list[float]:
    """
    Calcola le quote del bookmaker da probabilità e margine.

    Pipeline: probabilita → quote_giuste → quote_bookmaker
    Formula: quota_bookmaker = quota_giusta × (1 - margine)

    Args:
        probabilita: Lista di probabilità (somma = 1)
        margine: Overround (es. 0.05 per 5%)
        tolleranza: Tolleranza sulla somma delle probabilità

    Returns:
        Lista di quote del bookmaker
    """
    quote_fair = quote_giuste(probabilita, tolleranza)
    return quote_bookmaker(quote_fair, margine)


def quote_bookmaker(quote_giuste_val: list[float], margine: float) -> list[float]:
    """
    Applica il margine del bookmaker a una lista di quote giuste.

    Formula per ogni esito: quota_bookmaker = quota_giusta × (1 - margine)

    Args:
        quote_giuste_val: Lista di quote giuste (fair odds)
        margine: Overround in percentuale (es. 0.05 per 5%)

    Returns:
        Lista di quote del bookmaker

    Raises:
        ValueError: Se la lista è vuota o il margine non è valido
    """
    if not quote_giuste_val:
        raise ValueError("La lista di quote non può essere vuota")
    if margine < 0 or margine >= 1:
        raise ValueError("Il margine deve essere tra 0 (incluso) e 1 (escluso)")
    return [quota_bookmaker(q, margine) for q in quote_giuste_val]


def probabilita_implicita(quota: float) -> float:
    """
    Calcola la probabilità implicita da una quota.

    Formula: probabilita = 1 / quota

    Args:
        quota: Quota dell'evento

    Returns:
        La probabilità implicita (0 < p <= 1)

    Raises:
        ValueError: Se la quota non è valida
    """
    if quota <= 0:
        raise ValueError("La quota deve essere positiva")
    return 1.0 / quota


def calcola_vincita(puntata: float, quota: float) -> float:
    """
    Calcola la vincita totale (capitale restituito) per una scommessa vincente.

    Su una puntata di €10 con quota 2.00 si riceve €20 (profitto netto €10).

    Args:
        puntata: Importo scommesso
        quota: Quota dell'evento

    Returns:
        Vincita totale (puntata × quota)
    """
    if puntata < 0:
        raise ValueError("La puntata non può essere negativa")
    if quota <= 0:
        raise ValueError("La quota deve essere positiva")
    return puntata * quota


def calcola_profitto(puntata: float, quota: float, vinto: bool) -> float:
    """
    Calcola il profitto (o perdita) di una scommessa.

    Args:
        puntata: Importo scommesso
        quota: Quota dell'evento
        vinto: True se la scommessa è vinta

    Returns:
        Profitto positivo se vinto, -puntata se perso
    """
    if vinto:
        return calcola_vincita(puntata, quota) - puntata
    return -puntata


def calcola_overround(quote: list[float]) -> float:
    """
    Calcola l'overround dato da un set di quote del bookmaker.

    Formula: overround = sum(1/quota_i) - 1
    Valore 0.05 = 5% di margine del bookmaker.

    Args:
        quote: Lista delle quote del bookmaker per ogni esito

    Returns:
        Overround come valore tra 0 e 1 (es. 0.05 = 5%)

    Raises:
        ValueError: Se la lista è vuota
    """
    if not quote:
        raise ValueError("Serve almeno una quota")
    somma_probabilita = sum(1.0 / q for q in quote if q > 0)
    return somma_probabilita - 1.0


def margine_totale(quote: list[float]) -> float:
    """
    Calcola il margine totale (overround) di un mercato a quote multiple.

    Per un evento con N esiti: margine = sum(1/quota_i) - 1

    Args:
        quote: Lista delle quote di ogni esito

    Returns:
        Margine come valore tra 0 e 1 (es. 0.05 = 5%)
    """
    return calcola_overround(quote)


def stampa_prospetto_quote(
    probabilita: list[float],
    margine: float = 0.05,
    tolleranza: float = TOLERANZA_PROBABILITA,
) -> None:
    """
    Stampa un prospetto quote formattato con probabilità, quote giuste e quote bookmaker.

    Args:
        probabilita: Lista di probabilità (somma = 1)
        margine: Overround del bookmaker (default 5%)
        tolleranza: Tolleranza sulla somma delle probabilità
    """
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
