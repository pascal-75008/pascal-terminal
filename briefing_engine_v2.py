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
        model="claude-sonnet-4-20250514",
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
      "courtier": "s
