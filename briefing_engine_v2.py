import os,json,time,datetime,requests,anthropic

OUTPUT="docs/latest_briefing.json"
CACHE="docs/prices_cache.json"

MACRO={"S&P 500":"^GSPC","Nasdaq":"^NDX","CAC 40":"^FCHI","Or":"GC=F","Pétrole":"CL=F","EUR/USD":"EURUSD=X","VIX":"^VIX","Bitcoin":"BTC-USD"}

PORTFOLIO=[
    {"broker":"interactive_brokers","name":"Advanced Micro Devices","ticker":"AMD","qty":15,"pru":187.65,"currency":"USD"},
    {"broker":"interactive_brokers","name":"Amazon","ticker":"AMZN","qty":26,"pru":130.50,"currency":"USD"},
    {"broker":"interactive_brokers","name":"GlobalFoundries","ticker":"GFS","qty":95,"pru":55.20,"currency":"USD"},
    {"broker":"interactive_brokers","name":"Intel","ticker":"INTC","qty":60,"pru":33.40,"currency":"USD"},
    {"broker":"interactive_brokers","name":"Microsoft","ticker":"MSFT","qty":22,"pru":370.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"Meta Platforms","ticker":"META","qty":8,"pru":490.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"Nvidia","ticker":"NVDA","qty":10,"pru":88.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"Apple","ticker":"AAPL","qty":10,"pru":185.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"Palo Alto Networks","ticker":"PANW","qty":18,"pru":265.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"Palantir","ticker":"PLTR","qty":5,"pru":22.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"Netflix","ticker":"NFLX","qty":10,"pru":430.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"Tesla","ticker":"TSLA","qty":3,"pru":220.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"Zscaler","ticker":"ZS","qty":13,"pru":155.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"Enphase","ticker":"ENPH","qty":25,"pru":95.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"RTX Corp","ticker":"RTX","qty":5,"pru":90.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"IBM","ticker":"IBM","qty":10,"pru":145.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"Ondas","ticker":"ONDS","qty":130,"pru":3.50,"currency":"USD"},
    {"broker":"interactive_brokers","name":"UiPath","ticker":"PATH","qty":10,"pru":14.00,"currency":"USD"},
    {"broker":"boursorama","name":"Hermès","ticker":"RMS.PA","qty":10,"pru":1774.60,"currency":"EUR"},
    {"broker":"boursorama","name":"Alstom","ticker":"ALO.PA","qty":230,"pru":31.45,"currency":"EUR"},
    {"broker":"boursorama","name":"Edenred","ticker":"EDEN.PA","qty":60,"pru":43.61,"currency":"EUR"},
    {"broker":"boursorama","name":"Dassault Systèmes","ticker":"DSY.PA","qty":335,"pru":26.79,"currency":"EUR"},
    {"broker":"boursorama","name":"LVMH","ticker":"MC.PA","qty":12,"pru":482.08,"currency":"EUR"},
    {"broker":"boursorama","name":"Capgemini","ticker":"CAP.PA","qty":40,"pru":172.34,"currency":"EUR"},
    {"broker":"boursorama","name":"Sanofi","ticker":"SAN.PA","qty":51,"pru":81.83,"currency":"EUR"},
    {"broker":"boursorama","name":"Vinci","ticker":"DG.PA","qty":25,"pru":81.18,"currency":"EUR"},
    {"broker":"boursorama","name":"OVHcloud","ticker":"OVH.PA","qty":500,"pru":13.15,"currency":"EUR"},
    {"broker":"boursorama","name":"Spotify","ticker":"SPOT","qty":25,"pru":207.96,"currency":"USD"},
    {"broker":"boursorama","name":"ASML","ticker":"ASML","qty":6,"pru":1058.49,"currency":"USD"},
    {"broker":"boursorama","name":"Alphabet A","ticker":"GOOGL","qty":120,"pru":0,"currency":"USD"},
    {"broker":"boursorama","name":"Micron","ticker":"MU","qty":5,"pru":135.00,"currency":"USD"},
    {"broker":"boursorama","name":"Clariane","ticker":"CLARI.PA","qty":460,"pru":10.54,"currency":"EUR"},
    {"broker":"boursorama","name":"Elior","ticker":"ELIOR.PA","qty":70,"pru":19.69,"currency":"EUR"},
    {"broker":"boursorama","name":"BNP Paribas","ticker":"BNP.PA","qty":25,"pru":80.42,"currency":"EUR"},
    {"broker":"boursorama","name":"Pernod Ricard","ticker":"RI.PA","qty":54,"pru":71.35,"currency":"EUR"},
    {"broker":"linxea","name":"Amundi MSCI World IT","ticker":None,"qty":None,"pru":None,"currency":"EUR","value_eur":13069.81,"pv_eur":1583.60},
    {"broker":"linxea","name":"Ofi Precious Metals","ticker":None,"qty":None,"pru":None,"currency":"EUR","value_eur":12148.80,"pv_eur":662.55},
    {"broker":"linxea","name":"R-co Convertibles EU","ticker":None,"qty":None,"pru":None,"currency":"EUR","value_eur":11966.18,"pv_eur":479.88},
    {"broker":"linxea","name":"FCPR Ardian","ticker":None,"qty":None,"pru":None,"currency":"EUR","value_eur":10102.99,"pv_eur":115.49},
    {"broker":"linxea","name":"Amundi Nasdaq-100","ticker":None,"qty":None,"pru":None,"currency":"EUR","value_eur":1718.61,"pv_eur":219.84},
]

def load_cache():
    try:
        if os.path.exists(CACHE):
            with open(CACHE) as f: return json.load(f)
    except: pass
    return {}

def save_cache(c):
    os.makedirs(os.path.dirname(CACHE),exist_ok=True)
    with open(CACHE,"w") as f: json.dump(c,f)

def fetch_yahoo(ticker):
    try:
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
        h={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0","Accept":"application/json","Accept-Language":"en-US,en;q=0.9"}
        r=requests.get(url,headers=h,timeout=15)
        if r.status_code!=200: return None,0
        d=r.json()["chart"]["result"][0]
        closes=[c for c in d["indicators"]["quote"][0].get("close",[]) if c]
        price=d["meta"].get("regularMarketPrice") or (closes[-1] if closes else None)
        chg=(price-closes[0])/closes[0]*100 if closes and len(closes)>1 else 0
        return (round(price,2),round(chg,2)) if price else (None,0)
    except: return None,0

def fetch_av(ticker,key):
    if not key: return None,0
    try:
        clean=ticker.split(".")[0]
        r=requests.get(f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={clean}&apikey={key}",timeout=15)
        q=r.json().get("Global Quote",{})
        price=float(q.get("05. price",0))
        chg=float(q.get("10. change percent","0%").replace("%",""))
        return (round(price,2),round(chg,2)) if price>0 else (None,0)
    except: return None,0

def get_price(ticker,av_key,cache):
    if not ticker: return None,0
    price,chg=fetch_yahoo(ticker)
    if price:
        cache[ticker]={"price":price,"chg":chg,"date":str(datetime.date.today())}
        return price,chg
    time.sleep(1)
    price,chg=fetch_av(ticker,av_key)
    if price:
        print(f"    AV: {ticker}={price}")
        cache[ticker]={"price":price,"chg":chg,"date":str(datetime.date.today())}
        return price,chg
    if ticker in cache:
        c=cache[ticker]
        print(f"    Cache ({c.get('date','?')}): {ticker}={c['price']}")
        return c["price"],c.get("chg",0)
    return None,0

def main():
    av_key=os.environ.get("ALPHA_VANTAGE_KEY","")
    cache=load_cache()

    print("[1/4] Macro...")
    macro={}
    for name,ticker in MACRO.items():
        p,c=get_price(ticker,av_key,cache)
        macro[name]={"price":p,"week_chg":c}
        time.sleep(0.5)
    eurusd=macro.get("EUR/USD",{}).get("price") or 1.17

    print("[2/4] Portefeuille...")
    positions=[]
    total_eur=total_pv=0
    for pos in PORTFOLIO:
        p=dict(pos)
        if p["broker"]=="linxea":
            total_eur+=p.get("value_eur",0)
            total_pv+=p.get("pv_eur",0)
            positions.append(p)
            continue
        price,chg=get_price(p.get("ticker"),av_key,cache)
        p["price"]=price; p["week_chg"]=chg
        if price and p.get("qty") and p.get("pru") is not None:
            fx=(1/eurusd) if p["currency"]=="USD" else 1.0
            val=round(price*p["qty"]*fx,0)
            pv=round((price-p["pru"])*p["qty"]*fx,0)
            pvp=round((price-p["pru"])/p["pru"]*100,1) if p["pru"]>0 else 0
            p["value_eur"]=val; p["pv_eur"]=pv; p["pv_pct"]=pvp
            total_eur+=val; total_pv+=pv
        positions.append(p)
        time.sleep(0.3)

    save_cache(cache)
    print(f"    Total: {total_eur:,.0f}€ | PV: {total_pv:+,.0f}€")

    portfolio={
        "positions":sorted(positions,key=lambda x:abs(x.get("pv_eur") or 0),reverse=True)[:25],
        "total_value_eur":round(total_eur,0),"total_pv_eur":round(total_pv,0),
        "total_pv_pct":round(total_pv/total_eur*100,1) if total_eur else 0,
        "eurusd":eurusd,"brokers":["interactive_brokers","boursorama","linxea"]
    }

    print("[3/4] Claude...")
    client=anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    macro_str="\n".join([f"- {k}: {v['price']} ({v['week_chg']:+.1f}%)" for k,v in macro.items() if v.get("price")])
    top_mv=sorted([p for p in positions if (p.get("pv_eur") or 0)<0],key=lambda x:x.get("pv_eur",0))[:5]
    top_pv=sorted([p for p in positions if (p.get("pv_eur") or 0)>0],key=lambda x:x.get("pv_eur",0),reverse=True)[:5]
    mv_str="\n".join([f"- {p['name']}: {p.get('pv_pct',0):+.1f}% ({p.get('pv_eur',0):+,.0f}€)" for p in top_mv])
    pv_str="\n".join([f"- {p['name']}: {p.get('pv_pct',0):+.1f}% ({p.get('pv_eur',0):+,.0f}€)" for p in top_pv])

    msg=client.messages.create(
        model="claude-sonnet-4-5",max_tokens=3000,
        messages=[{"role":"user","content":f"""Tu es conseiller financier expert, trader professionnel.
Briefing samedi pour Pascal, avocat Paris. Portefeuille: {total_eur:,.0f}€ | PV/MV: {total_pv:+,.0f}€
Objectif: doubler en 5-7 ans (retraite). Budget CT: 1500-3000€. Courtiers: Boursorama, DeGiro, Linxea.

MACRO: {macro_str}
MEILLEURES PV: {pv_str}
PIRES MV: {mv_str}

Produis:
1. ORIENTATION: RISK_ON, RISK_OFF, ou MIXTE
2. RISQUE: FAIBLE, MODERE, ELEVE, ou EXTREME
3. RÉSUMÉ: 2 phrases
4. 5 ACTIONS PRIORITAIRES samedi (ticker | type | courtier | montant€ | entrée | cible | stop | raison)
5. 3 OPPORTUNITÉS CT hors portefeuille (ticker | thème | prix | cible | courtier | raison)
6. 3 CONVICTIONS LT retraite (ticker | thème | montant€ | thèse)
7. 3 DRIVERS MACRO (facteur | POSITIF/NEGATIF/NEUTRE | détail)
8. SECTEURS surpondérer / alléger
9. COMMENTAIRE du desk (3 paragraphes, style gérant hedge fund)"""}]
    )

    texte=msg.content[0].text
    print(f"    {len(texte)} caractères")

    print("[4/4] Sauvegarde...")
    result={
        "generated_at":datetime.datetime.now().isoformat(),
        "date":str(datetime.date.today()),
        "week_number":datetime.date.today().isocalendar()[1],
        "macro":macro,"portfolio":portfolio,
        "screened_count":len(PORTFOLIO),
        "backtest":{},"recent_calls":[],
        "analysis":{
            "semaine_en_bref":texte[:200].split("\n")[0],
            "orientation_marche":"RISK_ON" if "RISK_ON" in texte else "RISK_OFF" if "RISK_OFF" in texte else "MIXTE",
            "niveau_risque":"ELEVE" if "ELEVE" in texte else "EXTREME" if "EXTREME" in texte else "MODERE",
            "commentaire_weekend":texte,
            "actions_samedi_matin":[],"top_screener_ct":[],"top_screener_lt":[],
            "positions_a_surveiller":[],"macro_drivers":[],
            "secteurs":{"surponderer":[],"alleger":[]}
        }
    }

    os.makedirs(os.path.dirname(OUTPUT),exist_ok=True)
    with open(OUTPUT,"w",encoding="utf-8") as f:
        json.dump(result,f,ensure_ascii=False,separators=(",",":"))
    print(f"OK → {OUTPUT} ({os.path.getsize(OUTPUT):,} octets)")

if __name__=="__main__":
    main()
