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

    print("Appel Claude...")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    macro_str = "\n".join([
        f"- {k}: {v['price']} ({v['week_chg']:+.1f}% sem.)"
        for k, v in macro.items() if v["price"]
    ])

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        system="""Tu es un conseiller financier expert. Tu produis le briefing hebdomadaire de Pascal, 
investisseur parisien qui arbitre le samedi matin. Horizon 5-7 ans pour doubler son portefeuille.
Budget CT: 1500-3000€. Courtiers: Boursorama, DeGiro, Linxea.
Réponds UNIQUEMENT en JSON valide sans backticks:
{
  "semaine_en_bref": "string",
  "orientation_marche": "RISK_ON|RISK_OFF|MIXTE",
  "niveau_risque": "FAIBLE|MODERE|ELEVE|EXTREME",
  "actions_samedi_matin": [
    {
      "priorite": 1,
      "type": "ACHAT_CT|ACHAT_LT|VENTE|ALLEGER|SHORT",
      "ticker": "string",
      "nom": "string",
      "courtier": "DeGiro|Boursorama|Linxea",
      "montant_suggere": 0,
      "prix_entree": 0,
      "prix_cible": 0,
      "stop_loss": 0,
      "horizon": "CT_JOURS|CT_SEMAINES|MT_MOIS|LT_ANS",
      "conviction": 3,
      "rationale": "string",
      "risque_principal": "string",
      "disponible_pea": false
    }
  ],
  "top_screener_ct": [
    {
      "ticker": "string",
      "nom": "string",
      "theme": "string",
      "momentum_score": 0,
      "prix": 0,
      "cible_ct": 0,
      "courtier": "string",
      "rationale": "string"
    }
  ],
  "top_screener_lt": [
    {
      "ticker": "string",
      "nom": "string",
      "theme": "string",
      "these_retraite": "string",
      "montant_suggere": 0,
      "courtier": "string",
      "vehicule_linxea": null
    }
  ],
  "positions_a_surveiller": [
    {"ticker": "string", "nom": "string", "situation": "string", "action_si": "string"}
  ],
  "macro_drivers": [
    {"facteur": "string", "impact": "POSITIF|NEGATIF|NEUTRE", "detail": "string"}
  ],
  "secteurs": {"surponderer": [], "alleger": []},
  "commentaire_weekend": "string"
}""",
        messages=[{"role": "user", "content": f"""
DATE: {datetime.date.today().strftime('%A %d %B %Y')} (SAMEDI)
PORTEFEUILLE: ~236 000€ répartis sur IB (US tech), PEA/CTO (actions FR/EU), PER Linxea (fonds)
POSITIONS CLÉS EN MV: Alstom -44%, Edenred -51%, Clariane -60%, Elior -85%, Carmat -100%
POSITIONS CLÉS EN PV: Micron +408%, Spotify +77%, Blast Army +364%, ASML +27%, Vinci +57%
CASH DISPONIBLE: ~730€ sur IB

MACRO CETTE SEMAINE:
{macro_str}

Génère le briefing complet du samedi avec 6-8 actions prioritaires et 5 opportunités CT et LT.
"""}]
    )

    raw = message.content[0].text
    try:
        analysis = json.loads(raw)
    except:
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        analysis = json.loads(match.group()) if match else {"error": raw[:500]}

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
        "analysis": analysis,
    }

    os.makedirs("dashboard", exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Briefing généré: {OUTPUT}")

if __name__ == "__main__":
    main()
