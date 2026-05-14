"""
Pascal Terminal v2 — Portfolio Parser
Reads uploaded portfolio files (xlsx, csv) and normalizes positions.
Supports: Interactive Brokers xlsx, Boursorama csv, Linxea xlsx.
"""

import json
import re
import os
import io
from typing import Optional


def parse_number(s) -> Optional[float]:
    """Parse French/English formatted numbers."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    # Remove currency symbols and spaces used as thousands sep
    s = re.sub(r'[€$£\s]', '', s)
    s = s.replace('\xa0', '')
    # Handle French format: 1 234,56 -> 1234.56
    if ',' in s and '.' not in s:
        s = s.replace(' ', '').replace(',', '.')
    elif ',' in s and '.' in s:
        # 1.234,56 format
        s = s.replace('.', '').replace(',', '.')
    else:
        s = s.replace(' ', '')
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def detect_broker(filename: str, content_preview: str) -> str:
    """Detect which broker the file comes from."""
    fn = filename.lower()
    cp = content_preview.lower()

    if 'linxea' in fn or 'linxea' in cp or 'spirit' in cp:
        return 'linxea'
    if 'boursorama' in fn or 'export-positions' in fn:
        return 'boursorama'
    if 'portfolio' in fn or 'aperçu du portefeuille' in cp or 'ticker/isin' in cp:
        return 'interactive_brokers'
    if 'degiro' in fn:
        return 'degiro'
    return 'unknown'


def parse_interactive_brokers(data: list[dict]) -> list[dict]:
    """Parse IB portfolio xlsx format."""
    positions = []
    for row in data:
        # Skip cash and empty rows
        name = str(row.get('Produit', '') or '').strip()
        if not name or 'CASH' in name.upper():
            continue

        isin_ticker = str(row.get('Ticker/ISIN', '') or '').strip()
        qty = parse_number(row.get('Quantité'))
        price = parse_number(row.get('Clôture'))
        value_eur = parse_number(row.get('Montant en EUR'))
        currency = str(row.get('Devise', '') or row.get('Currency', 'USD')).strip()

        if not name or qty is None:
            continue

        # Try to extract ticker from ISIN or use name
        ticker = extract_ticker_from_isin_or_name(isin_ticker, name)

        positions.append({
            'broker':     'interactive_brokers',
            'name':       name,
            'ticker':     ticker,
            'isin':       isin_ticker if isin_ticker.startswith(('US','FR','DE','NL','KY','LU','IE','CA')) else '',
            'qty':        qty,
            'price':      price,
            'currency':   'EUR' if currency == 'EUR' or (value_eur and price and abs(value_eur - price * qty) < 1) else 'USD',
            'value_eur':  value_eur,
            'pru':        None,  # IB export doesn't include PRU directly
        })
    return positions


def parse_boursorama_csv(rows: list[dict]) -> list[dict]:
    """Parse Boursorama position export CSV."""
    positions = []
    for row in rows:
        name = str(row.get('name', '') or '').strip()
        if not name:
            continue

        isin = str(row.get('isin', '') or '').strip()
        qty = parse_number(row.get('quantity'))
        pru = parse_number(row.get('buyingPrice'))
        price = parse_number(row.get('lastPrice'))
        value = parse_number(row.get('amount'))
        variation = parse_number(row.get('variation'))

        ticker = extract_ticker_from_isin_or_name(isin, name)
        currency = 'USD' if ticker and not any(
            x in isin for x in ['FR','DE','NL','BE','IT','ES','PT','SE','DK','NO']
        ) else 'EUR'

        positions.append({
            'broker':    'boursorama',
            'name':      name,
            'ticker':    ticker,
            'isin':      isin,
            'qty':       qty,
            'price':     price,
            'currency':  currency,
            'value_eur': value,
            'pru':       pru,
            'pv_pct':    variation,
        })
    return positions


def parse_linxea(data: list[dict]) -> list[dict]:
    """Parse Linxea financial data xlsx."""
    positions = []
    for row in data:
        name = str(row.get('Nom du support', '') or '').strip()
        if not name:
            continue

        isin = str(row.get('ISIN', '') or '').strip()
        qty = parse_number(row.get('Nbre de parts'))
        price = parse_number(row.get('Dernière cotation'))
        value = parse_number(row.get('Somme en Compte'))
        pv = parse_number(row.get('Plus ou Moins Value'))
        pru = parse_number(row.get('Prix de Revient Moyen'))
        ytd = str(row.get('Perf.% Deb. année', '') or '').replace('%', '').replace(',', '.').strip()
        placement = str(row.get('Placement', '') or '').strip()
        category = str(row.get('Catégorie', '') or '').strip()

        try:
            ytd_pct = float(ytd)
        except (ValueError, TypeError):
            ytd_pct = None

        positions.append({
            'broker':    'linxea',
            'envelope':  placement,
            'name':      name,
            'ticker':    isin,  # use ISIN as identifier for funds
            'isin':      isin,
            'category':  category,
            'qty':       qty,
            'price':     price,
            'currency':  'EUR',
            'value_eur': value,
            'pru':       pru,
            'pv_eur':    pv,
            'ytd_pct':   ytd_pct,
        })
    return positions


ISIN_TICKER_MAP = {
    'US0079031078': 'AMD', 'US0231351067': 'AMZN', 'US0378331005': 'AAPL',
    'US4592001014': 'IBM', 'US4581401001': 'INTC', 'US4663131039': 'JBL',
    'US5949181045': 'MSFT', 'US67066G1040': 'NVDA', 'US64110L1061': 'NFLX',
    'US30303M1027': 'META', 'US6974351057': 'PANW', 'US75513E1010': 'RTX',
    'US7739031091': 'ROK', 'US83304A1060': 'SNAP', 'US88160R1014': 'TSLA',
    'US90364P1057': 'PATH', 'US98980G1022': 'ZS', 'US69608A1088': 'PLTR',
    'US29355A1079': 'ENPH', 'US09062X1037': 'BIIB', 'US68236H2040': 'ONDS',
    'KYG393871085': 'GFS',  # GlobalFoundries
    'FR0000052292': 'RMS.PA', 'FR0000120578': 'SAN.PA', 'FR0010220475': 'ALO.PA',
    'FR0010908533': 'EDEN.PA', 'FR0000120073': 'AI.PA', 'FR0000120271': 'TTE.PA',
    'FR0010208488': 'ENGI.PA', 'DE0007236101': 'SIE.DE', 'FR0000121014': 'MC.PA',
    'FR0000125486': 'VIE.PA', 'FR0000120693': 'RI.PA', 'FR0000125338': 'CAP.PA',
    'FR0014005HJ9': 'OVH.PA', 'FR0000120321': 'OR.PA', 'FR0000131104': 'BNP.PA',
    'FR0014003TT8': 'DSY.PA', 'NL0010273215': 'ASML',
    'US01609W1027': 'BABA', 'US88034P1093': 'TCEHY', 'US5951121038': 'MU',
    'US22788C1053': 'CRWD', 'US11135F1012': 'AVGO',
    'US02079K3059': 'GOOGL', 'US02079K1079': 'GOOG',
    'LU1778762911': 'SPOT',
}

NAME_TICKER_MAP = {
    'ADVANCED MICRO DEVICES': 'AMD', 'AMAZON.COM': 'AMZN', 'APPLE': 'AAPL',
    'MICROSOFT': 'MSFT', 'NVIDIA': 'NVDA', 'NETFLIX': 'NFLX', 'META PLATFORMS': 'META',
    'PALO ALTO NETWORKS': 'PANW', 'TESLA': 'TSLA', 'PALANTIR': 'PLTR',
    'ZSCALER': 'ZS', 'ENPHASE': 'ENPH', 'BIOGEN': 'BIIB',
    'INTEL': 'INTC', 'IBM': 'IBM', 'RTX': 'RTX', 'ROCKWELL': 'ROK',
    'GLOBALFOUNDRIES': 'GFS', 'JABIL': 'JBL', 'ONDAS': 'ONDS', 'SNAP': 'SNAP',
    'HERMES': 'RMS.PA', 'HERMÈS': 'RMS.PA', 'SANOFI': 'SAN.PA',
    'ALSTOM': 'ALO.PA', 'EDENRED': 'EDEN.PA', 'AIR LIQUIDE': 'AI.PA',
    'TOTALENERGIES': 'TTE.PA', 'ENGIE': 'ENGI.PA', 'SIEMENS': 'SIE.DE',
    'LVMH': 'MC.PA', 'VINCI': 'VIE.PA', 'PERNOD RICARD': 'RI.PA',
    'CAPGEMINI': 'CAP.PA', 'OVHCLOUD': 'OVH.PA', "L'OREAL": 'OR.PA',
    'LOREAL': 'OR.PA', 'BNP PARIBAS': 'BNP.PA', 'DASSAULT SYSTEMES': 'DSY.PA',
    'ASML': 'ASML', 'SPOTIFY': 'SPOT', 'ALIBABA': 'BABA', 'TENCENT': 'TCEHY',
    'MICRON': 'MU', 'CROWDSTRIKE': 'CRWD', 'BROADCOM': 'AVGO',
    'ALPHABET': 'GOOGL',
}


def extract_ticker_from_isin_or_name(isin_or_ticker: str, name: str) -> str:
    """Best-effort ticker extraction."""
    # Direct ISIN lookup
    if isin_or_ticker in ISIN_TICKER_MAP:
        return ISIN_TICKER_MAP[isin_or_ticker]

    # If it looks like a ticker already (short, uppercase, no spaces)
    if isin_or_ticker and len(isin_or_ticker) <= 6 and isin_or_ticker.upper() == isin_or_ticker:
        return isin_or_ticker

    # Name lookup (partial match)
    name_upper = name.upper()
    for key, ticker in NAME_TICKER_MAP.items():
        if key in name_upper:
            return ticker

    # Fallback: use first word of name
    return name.split()[0].upper()[:8] if name else isin_or_ticker


def normalize_portfolio(positions: list[dict]) -> dict:
    """Group positions by broker/envelope and compute totals."""
    by_broker = {}
    for pos in positions:
        broker = pos.get('broker', 'unknown')
        if broker not in by_broker:
            by_broker[broker] = []
        by_broker[broker].append(pos)

    total_eur = sum(p.get('value_eur', 0) or 0 for p in positions)

    return {
        'positions':   positions,
        'by_broker':   by_broker,
        'total_eur':   round(total_eur, 0),
        'count':       len(positions),
        'brokers':     list(by_broker.keys()),
    }


def parse_portfolio_file(filename: str, content: bytes) -> dict:
    """
    Main entry point. Parse any portfolio file and return normalized positions.
    Called from the web app when user uploads a file.
    """
    try:
        import openpyxl
        import csv

        ext = filename.lower().split('.')[-1]
        content_preview = ''

        if ext in ('xlsx', 'xls'):
            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return {'error': 'Fichier vide', 'positions': []}

            # First row as headers
            headers = [str(h or '').strip() for h in rows[0]]
            data = [dict(zip(headers, row)) for row in rows[1:] if any(c is not None for c in row)]
            content_preview = ' '.join(headers[:10]).lower()

            broker = detect_broker(filename, content_preview)

            if broker == 'linxea':
                positions = parse_linxea(data)
            elif broker == 'interactive_brokers':
                positions = parse_interactive_brokers(data)
            else:
                # Generic parse
                positions = parse_interactive_brokers(data)

        elif ext == 'csv':
            text = content.decode('utf-8-sig', errors='replace')
            content_preview = text[:500].lower()
            broker = detect_broker(filename, content_preview)

            # Try different separators
            for sep in [';', ',', '\t']:
                reader = csv.DictReader(io.StringIO(text), delimiter=sep)
                data = list(reader)
                if len(data) > 0 and len(data[0]) > 2:
                    break

            if broker == 'boursorama' or 'export-positions' in filename.lower():
                positions = parse_boursorama_csv(data)
            else:
                positions = parse_boursorama_csv(data)

        else:
            return {'error': f'Format non supporté: {ext}', 'positions': []}

        return normalize_portfolio(positions)

    except Exception as e:
        return {'error': str(e), 'positions': []}


if __name__ == "__main__":
    # Test with sample data
    test_row = {
        'Produit': 'NVIDIA CORP', 'Ticker/ISIN': 'US67066G1040',
        'Quantité': 10, 'Clôture': 225.83, 'Devise': 'USD', 'Montant en EUR': 1928.36
    }
    result = parse_interactive_brokers([test_row])
    print(json.dumps(result, indent=2, ensure_ascii=False))
