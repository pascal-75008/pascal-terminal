import os
import json
import datetime
import requests
import anthropic

OUTPUT = "dashboard/latest_briefing.json"

MACRO = {
    "S&P 500": "^GSPC", "Nasdaq": "^NDX", "CAC 40": "^FCHI",
    "Or": "GC=F", "Pétrole": "CL=F", "EUR/USD": "EURUSD=X",
    "VIX": "^VIX", "Bitcoin": "BTC-USD",
}

def fetch(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        meta = r.json()["chart"]["result"][0]["meta"]
        closes = [c for c in r.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"] if c]
        price = meta.get("regularMarketPrice") or closes[-1]
        chg = (price - closes[0]) / closes[0] * 100 if closes[0] else 0
        return {"price": round(price, 2), "week_chg": round(chg, 2)}
    except:
        return {"price": None, "week_chg": 0}

def main():
    print("Récupération macro...")
    macro = {name: fetch(ticker) for name, ticker in MACRO.items()}

    macro_str = "\n".join([
        f"- {k}: {v['price']} ({v['week_chg']:+.1f}% sem.)"
        for k, v in macro.items() if v["price"]
    ])

    print("Appel Claude...")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=3000,
        messages=[{"role": "user", "content": f"""Tu es un conseiller financier expert.
Produis le briefing du samedi pour Pascal, investisseur parisien, portefeuille ~236 000€.
Horizon 5-7 ans. Budget CT: 1500-3000€. Courtiers: Boursorama, DeGiro, Linxea.

MACRO:
{macro_str}

PORTEFEUILLE RÉSUMÉ:
- Grosses MV: Alstom -44%, Edenred -51%, Clariane -60%, Elior -85%
- Grosses PV: Micron +408%, Spotify +77%, ASML +27%
- Cash IB: 730€

Donne moi:
1. ORIENTATION (1 mot: RISK_ON, RISK_OFF, ou MIXTE)
2. RISQUE (1 mot: FAIBLE, MODERE, ELEVE, ou EXTREME)  
3. RÉSUMÉ (2 phrases max)
4. 5 ACTIONS PRIORITAIRES pour ce samedi (ticker, action, courtier, montant, prix entrée, cible, stop, raison courte)
5. 3 OPPORTUNITÉS CT hors portefeuille (ticker, thème, prix, cible, courtier, raison)
6. 3 CONVICTIONS LT retraite (ticker, thème, montant suggéré, raison en 1 phrase)
7. COMMENTAIRE GÉNÉRAL (3 paragraphes)

Réponds en texte structuré simple, pas de JSON."""}]
    )

    texte = message.content[0].text
    print("Réponse Claude reçue, longueur:", len(texte))

    result = {
        "generated_at": datetime.datetime.now().isoformat(),
        "date": datetime.date.today().isoformat(),
        "week_number": datetime.date.today().isocalendar()[1],
        "macro": macro,
        "portfolio": {
            "total_value_eur": 236000,
            "total_pv_eur": -15000,
            "total_pv_pct": -6.0,
            "eurusd": macro.get("EUR/USD", {}).get("price", 1.17),
            "positions": [],
            "brokers": ["interactive_brokers", "boursorama", "linxea"]
        },
        "screened_count": 50,
        "opportunities": {},
        "backtest": {},
        "recent_calls": [],
        "analysis": {
            "semaine_en_bref": texte[:300],
            "orientation_marche": "MIXTE",
            "niveau_risque": "MODERE",
            "commentaire_weekend": texte,
            "actions_samedi_matin": [],
            "top_screener_ct": [],
            "top_screener_lt": [],
            "positions_a_surveiller": [],
            "macro_drivers": [],
            "secteurs": {"surponderer": [], "alleger": []}
        }
    }

    os.makedirs("dashboard", exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Briefing généré avec succès!")

if __name__ == "__main__":
    main()
