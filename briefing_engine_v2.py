import os,json,time,datetime,requests,anthropic

OUTPUT="docs/latest_briefing.json"
CACHE="docs/prices_cache.json"

MACRO={"S&P 500":"^GSPC","Nasdaq":"^NDX","CAC 40":"^FCHI","Or":"GC=F","Pétrole":"CL=F","EUR/USD":"EURUSD=X","VIX":"^VIX","Bitcoin":"BTC-USD"}

# Portefeuille complet — mettre à jour après chaque ordre
PORTFOLIO=[
    # === INTERACTIVE BROKERS ===
    {"broker":"interactive_brokers","name":"ADR ON COMPASS PATHWAYS","ticker":"CPWR","qty":16,"pru":None,"currency":"USD"},
    {"broker":"interactive_brokers","name":"ADVANCED MICRO DEVICES","ticker":"AMD","qty":15,"pru":187.65,"currency":"USD"},
    {"broker":"interactive_brokers","name":"AEROVIRONMENT INC","ticker":"AVAV","qty":5,"pru":None,"currency":"USD"},
    {"broker":"interactive_brokers","name":"AMAZON.COM INC","ticker":"AMZN","qty":26,"pru":130.50,"currency":"USD"},
    {"broker":"interactive_brokers","name":"APPLE INC","ticker":"AAPL","qty":10,"pru":185.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"BIOGEN INC","ticker":"BIIB","qty":6,"pru":None,"currency":"USD"},
    {"broker":"interactive_brokers","name":"DEFINIUM THERAPEUTICS","ticker":"DFNM","qty":13,"pru":None,"currency":"USD"},
    {"broker":"interactive_brokers","name":"ENPHASE ENERGY INC","ticker":"ENPH","qty":25,"pru":95.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"GLOBALFOUNDRIES INC","ticker":"GFS","qty":1,"pru":None,"currency":"USD"},
    {"broker":"interactive_brokers","name":"HSBC HANG SENG TECH ETF","ticker":"3032.HK","qty":200,"pru":None,"currency":"HKD"},
    {"broker":"interactive_brokers","name":"INTEL CORP","ticker":"INTC","qty":1,"pru":None,"currency":"USD"},
    {"broker":"interactive_brokers","name":"IBM","ticker":"IBM","qty":10,"pru":145.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"JABIL INC","ticker":"JBL","qty":5,"pru":None,"currency":"USD"},
    {"broker":"interactive_brokers","name":"KYNDRYL HOLDINGS","ticker":"KD","qty":1,"pru":None,"currency":"USD"},
    {"broker":"interactive_brokers","name":"META PLATFORMS","ticker":"META","qty":8,"pru":490.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"MICROSOFT CORP","ticker":"MSFT","qty":22,"pru":370.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"NETFLIX INC","ticker":"NFLX","qty":10,"pru":430.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"NVIDIA CORP","ticker":"NVDA","qty":13,"pru":88.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"ONDAS INC","ticker":"ONDS","qty":130,"pru":3.50,"currency":"USD"},
    {"broker":"interactive_brokers","name":"PALANTIR TECHNOLOGIES","ticker":"PLTR","qty":5,"pru":22.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"PALO ALTO NETWORKS","ticker":"PANW","qty":18,"pru":265.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"ROCKWELL AUTOMATION","ticker":"ROK","qty":5,"pru":None,"currency":"USD"},
    {"broker":"interactive_brokers","name":"RTX CORP","ticker":"RTX","qty":5,"pru":90.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"SNAP INC","ticker":"SNAP","qty":8,"pru":12.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"TESLA INC","ticker":"TSLA","qty":3,"pru":220.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"TVARDI THERAPEUTICS","ticker":"TVRD","qty":1,"pru":None,"currency":"USD"},
    {"broker":"interactive_brokers","name":"UIPATH INC","ticker":"PATH","qty":10,"pru":14.00,"currency":"USD"},
    {"broker":"interactive_brokers","name":"ZSCALER INC","ticker":"ZS","qty":13,"pru":155.00,"currency":"USD"},
    # === BOURSORAMA PEA/CTO ===
    {"broker":"boursorama","name":"ALPHABET-A","ticker":"GOOGL","qty":120,"pru":None,"currency":"USD"},
    {"broker":"boursorama","name":"ALPHABET-C","ticker":"GOOG","qty":120,"pru":None,"currency":"USD"},
    {"broker":"boursorama","name":"HERMES INTL","ticker":"RMS.PA","qty":10,"pru":1774.60,"currency":"EUR"},
    {"broker":"boursorama","name":"SPOTIFY TECH","ticker":"SPOT","qty":25,"pru":207.96,"currency":"USD"},
    {"broker":"boursorama","name":"L'OREAL","ticker":"OR.PA","qty":25,"pru":376.38,"currency":"EUR"},
    {"broker":"boursorama","name":"ESSILORLUXOTTICA","ticker":"EL.PA","qty":50,"pru":217.52,"currency":"EUR"},
    {"broker":"boursorama","name":"ASML HLDG","ticker":"ASML","qty":6,"pru":1058.49,"currency":"USD"},
    {"broker":"boursorama","name":"MICROSOFT","ticker":"MSFT","qty":22,"pru":None,"currency":"USD"},
    {"broker":"boursorama","name":"BROADCOM","ticker":"AVGO","qty":20,"pru":291.53,"currency":"USD"},
    {"broker":"boursorama","name":"ALIBABA GROUP","ticker":"BABA","qty":55,"pru":125.54,"currency":"USD"},
    {"broker":"boursorama","name":"DASSAULT SYSTEMES","ticker":"DSY.PA","qty":335,"pru":26.79,"currency":"EUR"},
    {"broker":"boursorama","name":"OVHCLOUD","ticker":"OVH.PA","qty":500,"pru":13.15,"currency":"EUR"},
    {"broker":"boursorama","name":"AMUNDI PEA US TECH","ticker":"PUST.PA","qty":70,"pru":57.71,"currency":"EUR"},
    {"broker":"boursorama","name":"LVMH","ticker":"MC.PA","qty":12,"pru":482.08,"currency":"EUR"},
    {"broker":"boursorama","name":"TENCENT ADR","ticker":"TCEHY","qty":680,"pru":15.41,"currency":"USD"},
    {"broker":"boursorama","name":"BLAST ARMY","ticker":None,"qty":1000,"pru":1.00,"currency":"EUR","price_fixed":4.64},
    {"broker":"boursorama","name":"SOITEC","ticker":"SOI.PA","qty":30,"pru":169.11,"currency":"EUR"},
    {"broker":"boursorama","name":"ALSTOM","ticker":"ALO.PA","qty":230,"pru":31.45,"currency":"EUR"},
    {"broker":"boursorama","name":"CAPGEMINI","ticker":"CAP.PA","qty":40,"pru":172.34,"currency":"EUR"},
    {"broker":"boursorama","name":"ISHARES DIGITAL SECURITY","ticker":"LOCK.PA","qty":399,"pru":8.37,"currency":"EUR"},
    {"broker":"boursorama","name":"SANOFI","ticker":"SAN.PA","qty":51,"pru":81.83,"currency":"EUR"},
    {"broker":"boursorama","name":"MICRON TECHNOLOGY","ticker":"MU","qty":5,"pru":135.00,"currency":"USD"},
    {"broker":"boursorama","name":"PERNOD RICARD","ticker":"RI.PA","qty":54,"pru":71.35,"currency":"EUR"},
    {"broker":"boursorama","name":"VINCI","ticker":"DG.PA","qty":25,"pru":81.18,"currency":"EUR"},
    {"broker":"boursorama","name":"AMUNDI PEA EAU","ticker":"WATR.PA","qty":100,"pru":21.17,"currency":"EUR"},
    {"broker":"boursorama","name":"OPMOBILITY","ticker":"POM.PA","qty":150,"pru":20.72,"currency":"EUR"},
    {"broker":"boursorama","name":"CROWDSTRIKE","ticker":"CRWD","qty":5,"pru":408.74,"currency":"USD"},
    {"broker":"boursorama","name":"COREWEAVE","ticker":"CRWV","qty":25,"pru":120.45,"currency":"USD"},
    {"broker":"boursorama","name":"BNP PARIBAS","ticker":"BNP.PA","qty":25,"pru":80.42,"currency":"EUR"},
    {"broker":"boursorama","name":"SMCP","ticker":"SMCP.PA","qty":450,"pru":10.82,"currency":"EUR"},
    {"broker":"boursorama","name":"CLARIANE","ticker":"CLARI.PA","qty":460,"pru":10.54,"currency":"EUR"},
    {"broker":"boursorama","name":"NEXTERA ENERGY","ticker":"NEE","qty":20,"pru":64.38,"currency":"USD"},
    {"broker":"boursorama","name":"HONEYWELL INTL","ticker":"HON","qty":8,"pru":197.13,"currency":"USD"},
    {"broker":"boursorama","name":"INTUITIVE SURGICAL","ticker":"ISRG","qty":4,"pru":573.59,"currency":"USD"},
    {"broker":"boursorama","name":"AMUNDI STOXX HEALTH","ticker":"HLTH.PA","qty":10,"pru":141.03,"currency":"EUR"},
    {"broker":"boursorama","name":"CARREFOUR","ticker":"CA.PA","qty":80,"pru":17.93,"currency":"EUR"},
    {"broker":"boursorama","name":"EDENRED","ticker":"EDEN.PA","qty":60,"pru":43.61,"currency":"EUR"},
    {"broker":"boursorama","name":"BLAST ARMY 2","ticker":None,"qty":847,"pru":1.00,"currency":"EUR","price_fixed":1.46},
    {"broker":"boursorama","name":"IMERYS","ticker":"NK.PA","qty":30,"pru":43.48,"currency":"EUR"},
    {"broker":"boursorama","name":"TERACT","ticker":"TRACT.PA","qty":200,"pru":11.24,"currency":"EUR"},
    {"broker":"boursorama","name":"ORANGE","ticker":"ORA.PA","qty":15,"pru":50.87,"currency":"EUR"},
    {"broker":"boursorama","name":"SIEMENS","ticker":"SIE.DE","qty":1,"pru":120.35,"currency":"EUR"},
    {"broker":"boursorama","name":"GE AEROSPACE","ticker":"GE","qty":1,"pru":106.80,"currency":"USD"},
    {"broker":"boursorama","name":"ELIOR GROUP","ticker":"ELIOR.PA","qty":70,"pru":19.69,"currency":"EUR"},
    {"broker":"boursorama","name":"REMY COINTREAU","ticker":"RCO.PA","qty":5,"pru":97.09,"currency":"EUR"},
    {"broker":"boursorama","name":"AIR LIQUIDE","ticker":"AI.PA","qty":1,"pru":88.00,"currency":"EUR"},
    {"broker":"boursorama","name":"PDD HOLDINGS","ticker":"PDD","qty":10,"pru":87.92,"currency":"USD"},
    {"broker":"boursorama","name":"BAIDU ADR","ticker":"BIDU","qty":1,"pru":105.38,"currency":"USD"},
    {"broker":"boursorama","name":"AIRBNB","ticker":"ABNB","qty":1,"pru":124.66,"currency":"USD"},
    {"broker":"boursorama","name":"TOTALENERGIES","ticker":"TTE.PA","qty":1,"pru":36.91,"currency":"EUR"},
    {"broker":"boursorama","name":"NIO ADR","ticker":"NIO","qty":1,"pru":4.07,"currency":"USD"},
    {"broker":"boursorama","name":"SALESFORCE","ticker":"CRM","qty":1,"pru":191.38,"currency":"USD"},
    {"broker":"boursorama","name":"SOLSTICE ADVA","ticker":"SLGD","qty":2,"pru":42.42,"currency":"USD"},
    {"broker":"boursorama","name":"EUROFINS SCIENTIFIC","ticker":"ERF.PA","qty":1,"pru":75.42,"currency":"EUR"},
    {"broker":"boursorama","name":"BOLLORE SE","ticker":"BOL.PA","qty":1,"pru":3.68,"currency":"EUR"},
    {"broker":"boursorama","name":"VIRGIN GALACTIC","ticker":"SPCE","qty":7,"pru":470.48,"currency":"USD"},
    {"broker":"boursorama","name":"CARMAT","ticker":"ALCAR.PA","qty":170,"pru":24.35,"currency":"EUR"},
    {"broker":"boursorama","name":"CNIM GROUP","ticker":None,"qty":40,"pru":133.81,"currency":"EUR","price_fixed":0.0},
    # === LINXEA PER (valeur fixe — pas de ticker Yahoo) ===
    {"broker":"linxea","name":"Amundi MSCI World IT","ticker":None,"qty":None,"pru":None,"currency":"EUR","value_eur":13069.81,"pv_eur":1583.60,"pv_pct":13.8},
    {"broker":"linxea","name":"Ofi Precious Metals","ticker":None,"qty":None,"pru":None,"currency":"EUR","value_eur":12148.80,"pv_eur":662.55,"pv_pct":5.8},
    {"broker":"linxea","name":"R-co Convertibles EU","ticker":None,"qty":None,"pru":None,"currency":"EUR","value_eur":11966.18,"pv_eur":479.88,"pv_pct":4.2},
    {"broker":"linxea","name":"FCPR Ardian Multi strat.","ticker":None,"qty":None,"pru":None,"currency":"EUR","value_eur":10102.99,"pv_eur":115.49,"pv_pct":1.2},
    {"broker":"linxea","name":"Amundi Nasdaq-100 Swap","ticker":None,"qty":None,"pru":None,"currency":"EUR","value_eur":1718.61,"pv_eur":219.84,"pv_pct":14.7},
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
        h={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36","Accept":"application/json"}
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
    print(f"    EUR/USD: {eurusd}")

    print("[2/4] Portefeuille...")
    positions=[]
    total_eur=total_pv=0

    for pos in PORTFOLIO:
        p=dict(pos)

        # Linxea: valeur fixe
        if p["broker"]=="linxea":
            total_eur+=p.get("value_eur",0)
            total_pv+=p.get("pv_eur",0)
            p["week_chg"]=0
            positions.append(p)
            continue

        # Prix fixe (BLAST ARMY, CNIM, etc.)
        if p.get("price_fixed") is not None:
            price=p["price_fixed"]
            p["price"]=price
            p["week_chg"]=0
            if p.get("qty") and p.get("pru") is not None:
                val=round(price*p["qty"],0)
                pv=round((price-p["pru"])*p["qty"],0)
                pvp=round((price-p["pru"])/p["pru"]*100,1) if p["pru"]>0 else 0
                p["value_eur"]=val; p["pv_eur"]=pv; p["pv_pct"]=pvp
                total_eur+=val; total_pv+=pv
            positions.append(p)
            continue

        # Récupération prix live
        ticker=p.get("ticker")
        price,chg=get_price(ticker,av_key,cache)
        p["price"]=price; p["week_chg"]=chg

        if price and p.get("qty"):
            fx=(1/eurusd) if p["currency"]=="USD" else 1.0
            val=round(price*p["qty"]*fx,0)
            p["value_eur"]=val
            total_eur+=val
            if p.get("pru") is not None and p["pru"]>0:
                pv=round((price-p["pru"])*p["qty"]*fx,0)
                pvp=round((price-p["pru"])/p["pru"]*100,1)
                p["pv_eur"]=pv; p["pv_pct"]=pvp
                total_pv+=pv

        positions.append(p)
        time.sleep(0.3)

    save_cache(cache)

    # Nettoyer les champs internes avant export
    for p in positions:
        p.pop("price_fixed",None)

    # Trier par valeur EUR décroissante
    positions_sorted=sorted(positions,key=lambda x:x.get("value_eur") or 0,reverse=True)

    print(f"    Total: {total_eur:,.0f}€ | PV: {total_pv:+,.0f}€ | {len(positions)} positions")

    portfolio={
        "positions":positions_sorted,
        "total_value_eur":round(total_eur,0),
        "total_pv_eur":round(total_pv,0),
        "total_pv_pct":round(total_pv/total_eur*100,1) if total_eur else 0,
        "eurusd":eurusd,
        "brokers":["boursorama","interactive_brokers","linxea"]
    }

    print("[3/4] Claude...")
    client=anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    macro_str="\n".join([f"- {k}: {v['price']} ({v['week_chg']:+.1f}%)" for k,v in macro.items() if v.get("price")])
    top_mv=sorted([p for p in positions if (p.get("pv_eur") or 0)<0],key=lambda x:x.get("pv_eur",0))[:6]
    top_pv=sorted([p for p in positions if (p.get("pv_eur") or 0)>0],key=lambda x:x.get("pv_eur",0),reverse=True)[:6]
    mv_str="\n".join([f"- {p['name']}: {p.get('pv_pct',0):+.1f}% ({p.get('pv_eur',0):+,.0f}€)" for p in top_mv])
    pv_str="\n".join([f"- {p['name']}: {p.get('pv_pct',0):+.1f}% ({p.get('pv_eur',0):+,.0f}€)" for p in top_pv])

    msg=client.messages.create(
        model="claude-sonnet-4-5",max_tokens=3000,
        messages=[{"role":"user","content":f"""Tu es conseiller financier expert, trader professionnel.
Briefing samedi pour Pascal, avocat Paris. Portefeuille: {total_eur:,.0f}€ | PV/MV: {total_pv:+,.0f}€
Objectif: doubler en 5-7 ans (retraite). Budget CT: 1500-3000€. Courtiers: Boursorama, DeGiro, Linxea.

MACRO SEMAINE:
{macro_str}

MEILLEURES PV:
{pv_str}

PIRES MV:
{mv_str}

Produis le briefing du samedi:
1. ORIENTATION: RISK_ON, RISK_OFF, ou MIXTE
2. RISQUE: FAIBLE, MODERE, ELEVE, ou EXTREME
3. RÉSUMÉ: 2 phrases percutantes
4. 5 ACTIONS PRIORITAIRES ce samedi (ticker | type ACHAT_CT/ACHAT_LT/VENTE/ALLEGER/SHORT/SURVEILLER | courtier Boursorama/DeGiro/Linxea | montant€ | prix entrée | cible | stop | raison courte)
5. 3 OPPORTUNITÉS CT hors portefeuille avec thème macro (tensions géopolitiques, IA, GLP-1, défense, uranium, etc.)
6. 3 CONVICTIONS LT retraite 5-7 ans
7. 3 DRIVERS MACRO impactant le portefeuille
8. SECTEURS à surpondérer / alléger
9. COMMENTAIRE du desk style gérant hedge fund (3 paragraphes)

Réponds en texte structuré clair."""}]
    )

    texte=msg.content[0].text
    print(f"    Claude: {len(texte)} caractères")

    print("[4/4] Sauvegarde dans docs/...")
    result={
        "generated_at":datetime.datetime.now().isoformat(),
        "date":str(datetime.date.today()),
        "week_number":datetime.date.today().isocalendar()[1],
        "macro":macro,
        "portfolio":portfolio,
        "screened_count":len(positions),
        "backtest":{},"recent_calls":[],
        "analysis":{
            "semaine_en_bref":texte[:200].split("\n")[0].replace("1.","").replace("ORIENTATION:","").strip(),
            "orientation_marche":"RISK_ON" if "RISK_ON" in texte else "RISK_OFF" if "RISK_OFF" in texte else "MIXTE",
            "niveau_risque":"EXTREME" if "EXTREME" in texte else "ELEVE" if "ELEVE" in texte else "MODERE" if "MODERE" in texte else "FAIBLE",
            "commentaire_weekend":texte,
            "actions_samedi_matin":[],"top_screener_ct":[],"top_screener_lt":[],
            "positions_a_surveiller":[],"macro_drivers":[],
            "secteurs":{"surponderer":[],"alleger":[]}
        }
    }

    os.makedirs(os.path.dirname(OUTPUT),exist_ok=True)
    with open(OUTPUT,"w",encoding="utf-8") as f:
        json.dump(result,f,ensure_ascii=False,separators=(",",":"))

    size=os.path.getsize(OUTPUT)
    print(f"OK → {OUTPUT} ({size:,} octets | {len(positions)} positions)")

if __name__=="__main__":
    main()
