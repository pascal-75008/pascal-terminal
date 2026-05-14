"""
Pascal Terminal v2 — Email Sender
Generates and sends the Saturday morning briefing email.
"""

import os
import json
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def action_badge_html(a: str) -> str:
    colors = {
        "ACHAT_CT":   ("#EAF3DE","#2d6a1f"),
        "ACHAT_LT":   ("#e0f5ee","#065040"),
        "VENTE":      ("#FCEBEB","#8b2020"),
        "ALLEGER":    ("#FAEEDA","#7a4500"),
        "SHORT":      ("#EEEDFE","#3a2d8a"),
        "HEDGER":     ("#EEEDFE","#3a2d8a"),
        "SURVEILLER": ("#e3eefa","#1a4f8a"),
    }
    bg, fg = colors.get(a, ("#f0efe8","#555"))
    return f'<span style="background:{bg};color:{fg};padding:3px 9px;border-radius:12px;font-size:11px;font-weight:700">{a}</span>'


def broker_badge_html(b: str) -> str:
    colors = {
        "DeGiro":    ("#e8f5e0","#2d6a1f"),
        "Boursorama":("#e3eefa","#1a4f8a"),
        "Linxea":    ("#fef3e0","#7a4500"),
    }
    bg, fg = colors.get(b, ("#f0f0f0","#555"))
    return f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600">{b}</span>'


def stars_html(n: int) -> str:
    return "★" * n + "☆" * (5 - n)


def pct_html(v: float) -> str:
    if v is None:
        return "—"
    color = "#2d6a1f" if v >= 0 else "#8b2020"
    sign  = "+" if v >= 0 else ""
    return f'<span style="color:{color};font-weight:500">{sign}{v:.1f}%</span>'


def build_html_email(data: dict) -> str:
    a  = data.get("analysis", {})
    p  = data.get("portfolio", {})
    bt = data.get("backtest", {})
    date_str = data.get("date", datetime.date.today().isoformat())
    week_num = data.get("week_number", "")
    gen_at   = (data.get("generated_at",""))[:16].replace("T"," ")
    tv  = p.get("total_value_eur", 0)
    pv  = p.get("total_pv_eur", 0)
    pvp = p.get("total_pv_pct", 0)
    pv_color = "#2d6a1f" if pv >= 0 else "#8b2020"

    actions = a.get("actions_samedi_matin", [])

    or_map = {"RISK_ON":"#EAF3DE;color:#2d6a1f","RISK_OFF":"#FCEBEB;color:#8b2020","MIXTE":"#FAEEDA;color:#7a4500"}
    or_style = or_map.get(a.get("orientation_marche","MIXTE"), "#f0efe8;color:#555")

    rl_map = {"FAIBLE":"#e0f5ee;color:#065040","MODERE":"#FAEEDA;color:#7a4500","ELEVE":"#FCEBEB;color:#8b2020","EXTREME":"#EEEDFE;color:#3a2d8a"}
    rl_style = rl_map.get(a.get("niveau_risque","MODERE"), "#FAEEDA;color:#7a4500")

    # Actions table rows
    action_rows = ""
    for i, act in enumerate(actions):
        prio_color = "#8b2020" if i==0 else "#7a4500" if i<=2 else "#2d6a1f"
        pea = '<span style="background:#e0f5ee;color:#065040;padding:1px 6px;border-radius:8px;font-size:10px">PEA</span>' if act.get("disponible_pea") else ""
        action_rows += f"""
        <tr style="border-bottom:0.5px solid #e8e8e8">
          <td style="padding:10px 8px;font-size:20px;font-weight:800;color:{prio_color};text-align:center">{act.get('priorite',i+1)}</td>
          <td style="padding:10px 8px">{action_badge_html(act.get('type',''))}</td>
          <td style="padding:10px 8px">
            <strong style="font-size:13px">{act.get('nom','')}</strong><br>
            <span style="color:#888;font-size:11px">{act.get('ticker','')} {pea}</span>
          </td>
          <td style="padding:10px 8px">{broker_badge_html(act.get('courtier',''))}</td>
          <td style="padding:10px 8px;text-align:right;font-weight:600;font-size:13px">
            {f"{int(act['montant_suggere']):,}€".replace(",","&nbsp;") if act.get('montant_suggere') else '—'}
          </td>
          <td style="padding:10px 8px;text-align:right">{act.get('prix_entree','—')}</td>
          <td style="padding:10px 8px;text-align:right;color:#2d6a1f;font-weight:500">{act.get('prix_cible','—')}</td>
          <td style="padding:10px 8px;text-align:right;color:#8b2020">{act.get('stop_loss','—')}</td>
          <td style="padding:10px 8px;text-align:center;color:#c48a00">{stars_html(act.get('conviction',3))}</td>
          <td style="padding:10px 8px;font-size:11px;color:#666;max-width:180px">
            {act.get('rationale','')}<br>
            <span style="color:#c0392b">⚠ {act.get('risque_principal','')}</span>
          </td>
        </tr>"""

    # Top CT screener
    ct_rows = ""
    for opp in a.get("top_screener_ct", [])[:6]:
        ct_rows += f"""
        <tr style="border-bottom:0.5px solid #e8e8e8">
          <td style="padding:8px">{opp.get('nom','')}<br><span style="color:#888;font-size:11px">{opp.get('ticker','')} · {opp.get('theme','')}</span></td>
          <td style="padding:8px">{broker_badge_html(opp.get('courtier',''))}</td>
          <td style="padding:8px;text-align:right;font-weight:500">{opp.get('prix','—')}</td>
          <td style="padding:8px;text-align:right;color:#2d6a1f">{opp.get('cible_ct','—')}</td>
          <td style="padding:8px">{opp.get('rationale','')[:80]}...</td>
        </tr>"""

    # Top LT
    lt_cards = ""
    for opp in a.get("top_screener_lt", [])[:5]:
        lx = f'<br><span style="background:#fef3e0;color:#7a4500;padding:1px 6px;border-radius:8px;font-size:10px">Linxea: {opp["vehicule_linxea"]}</span>' if opp.get("vehicule_linxea") else ""
        lt_cards += f"""
        <div style="border-left:3px solid #065040;padding:10px 14px;background:#f8f8f5;border-radius:0 8px 8px 0;margin-bottom:8px">
          <div style="font-weight:600;font-size:13px">{opp.get('nom','')} <span style="color:#888;font-size:11px">{opp.get('ticker','')}</span>{lx}</div>
          <div style="font-size:12px;color:#555;margin-top:4px;font-style:italic">"{opp.get('these_retraite','')}"</div>
          <div style="margin-top:6px">{broker_badge_html(opp.get('courtier',''))}
            <span style="background:#f0efe8;color:#555;padding:2px 8px;border-radius:10px;font-size:11px;margin-left:6px">
              Montant suggéré: {f"{int(opp['montant_suggere']):,}€".replace(',','&nbsp;') if opp.get('montant_suggere') else '?'}
            </span>
          </div>
        </div>"""

    # Macro
    macro_rows = ""
    for name, vals in (data.get("macro") or {}).items():
        if not vals.get("price"):
            continue
        chg = vals.get("week_chg", 0)
        macro_rows += f"""
        <tr style="border-bottom:0.5px solid #e8e8e8">
          <td style="padding:6px 8px;color:#666">{name}</td>
          <td style="padding:6px 8px;text-align:right;font-weight:500">{vals['price']:,.2f}</td>
          <td style="padding:6px 8px;text-align:right">{pct_html(chg)}</td>
        </tr>"""

    # Drivers
    driver_rows = ""
    impact_colors = {"POSITIF": "#065040", "NEGATIF": "#8b2020", "NEUTRE": "#555"}
    for d in a.get("macro_drivers", []):
        c = impact_colors.get(d.get("impact","NEUTRE"), "#555")
        driver_rows += f"""
        <tr style="border-bottom:0.5px solid #e8e8e8">
          <td style="padding:7px 8px"><span style="color:{c};font-weight:600">{d.get('impact','')}</span></td>
          <td style="padding:7px 8px;font-weight:500">{d.get('facteur','')}</td>
          <td style="padding:7px 8px;color:#666;font-size:12px">{d.get('detail','')}</td>
        </tr>"""

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Pascal Terminal — Samedi Semaine {week_num}</title></head>
<body style="margin:0;padding:0;background:#f0efe8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
<div style="max-width:820px;margin:0 auto;padding:20px 12px">

<!-- HEADER -->
<div style="background:#161616;border-radius:12px 12px 0 0;padding:20px 24px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px">
    <div>
      <div style="color:#fff;font-size:18px;font-weight:700">Pascal Terminal <span style="color:#555;font-size:12px;font-weight:400">v2</span></div>
      <div style="color:#888;font-size:11px;margin-top:2px">Briefing Samedi · Semaine {week_num} · {date_str} · {gen_at}</div>
    </div>
    <div>
      <span style="background:{or_style};padding:5px 14px;border-radius:20px;font-size:12px;font-weight:700;margin-right:6px">{a.get('orientation_marche','?')}</span>
      <span style="background:{rl_style};padding:5px 14px;border-radius:20px;font-size:12px;font-weight:700">Risque {a.get('niveau_risque','?')}</span>
    </div>
  </div>
  <div style="color:#aaa;font-size:13px;margin-top:14px;line-height:1.7;border-top:1px solid #2a2a2a;padding-top:12px">
    {a.get('semaine_en_bref','')}</div>
</div>

<!-- METRICS -->
<div style="background:#fff;padding:16px 24px;display:flex;gap:10px;flex-wrap:wrap;border-bottom:1px solid #eee">
  <div style="flex:1;min-width:130px;background:#f8f8f5;border-radius:8px;padding:12px 14px">
    <div style="font-size:11px;color:#888;margin-bottom:3px">Portefeuille total</div>
    <div style="font-size:22px;font-weight:700">{int(tv):,}€</div>
  </div>
  <div style="flex:1;min-width:130px;background:#f8f8f5;border-radius:8px;padding:12px 14px">
    <div style="font-size:11px;color:#888;margin-bottom:3px">PV / MV globale</div>
    <div style="font-size:22px;font-weight:700;color:{pv_color}">{'+' if pv>=0 else ''}{int(pv):,}€</div>
    <div style="font-size:12px;color:{pv_color}">{'+' if pvp>=0 else ''}{pvp:.1f}%</div>
  </div>
  <div style="flex:1;min-width:130px;background:#f8f8f5;border-radius:8px;padding:12px 14px">
    <div style="font-size:11px;color:#888;margin-bottom:3px">Hit rate Claude</div>
    <div style="font-size:22px;font-weight:700;color:{'#2d6a1f' if (bt.get('hit_rate') or 0)>=60 else '#8b2020'}">{bt.get('hit_rate','—')}{('%' if bt.get('hit_rate') else '')}</div>
    <div style="font-size:12px;color:#888">{bt.get('evaluated',0)} reco évaluées</div>
  </div>
  <div style="flex:1;min-width:130px;background:#f8f8f5;border-radius:8px;padding:12px 14px">
    <div style="font-size:11px;color:#888;margin-bottom:3px">Instruments scannés</div>
    <div style="font-size:22px;font-weight:700">{data.get('screened_count',0)}</div>
    <div style="font-size:12px;color:#888">univers mondial</div>
  </div>
</div>

<!-- PLAN D'ACTION SAMEDI -->
<div style="background:#fff;padding:16px 24px;border-bottom:1px solid #eee">
  <div style="font-size:12px;font-weight:700;color:#888;letter-spacing:.05em;margin-bottom:12px">PLAN D'ACTION DU SAMEDI — ORDONNÉ PAR PRIORITÉ</div>
  <div style="overflow-x:auto">
  <table style="width:100%;border-collapse:collapse;font-size:13px">
    <thead><tr style="border-bottom:2px solid #1a1a1a">
      <th style="padding:8px;text-align:center;font-size:11px;color:#888">#</th>
      <th style="padding:8px;font-size:11px;color:#888">TYPE</th>
      <th style="padding:8px;font-size:11px;color:#888">VALEUR</th>
      <th style="padding:8px;font-size:11px;color:#888">COURTIER</th>
      <th style="padding:8px;text-align:right;font-size:11px;color:#888">MONTANT</th>
      <th style="padding:8px;text-align:right;font-size:11px;color:#888">ENTRÉE</th>
      <th style="padding:8px;text-align:right;font-size:11px;color:#888">CIBLE</th>
      <th style="padding:8px;text-align:right;font-size:11px;color:#888">STOP</th>
      <th style="padding:8px;text-align:center;font-size:11px;color:#888">CONV.</th>
      <th style="padding:8px;font-size:11px;color:#888">RATIONALE & RISQUE</th>
    </tr></thead>
    <tbody>{action_rows}</tbody>
  </table></div>
</div>

<!-- TOP CT SCREENER -->
<div style="background:#fff;padding:16px 24px;border-bottom:1px solid #eee">
  <div style="font-size:12px;font-weight:700;color:#888;letter-spacing:.05em;margin-bottom:10px">
    TOP SCREENER CT — OPPORTUNITÉS HORS PORTEFEUILLE (quelques jours/semaines)</div>
  <div style="overflow-x:auto">
  <table style="width:100%;border-collapse:collapse;font-size:13px">
    <thead><tr style="border-bottom:1.5px solid #1a1a1a">
      <th style="padding:7px 8px;font-size:11px;color:#888">Valeur / Thème</th>
      <th style="padding:7px 8px;font-size:11px;color:#888">Courtier</th>
      <th style="padding:7px 8px;text-align:right;font-size:11px;color:#888">Prix</th>
      <th style="padding:7px 8px;text-align:right;font-size:11px;color:#888">Cible CT</th>
      <th style="padding:7px 8px;font-size:11px;color:#888">Thèse courte</th>
    </tr></thead>
    <tbody>{ct_rows}</tbody>
  </table></div>
</div>

<!-- TOP LT RETRAITE -->
<div style="background:#fff;padding:16px 24px;border-bottom:1px solid #eee">
  <div style="font-size:12px;font-weight:700;color:#888;letter-spacing:.05em;margin-bottom:10px">
    CONVICTIONS LONG TERME — RETRAITE (5-7 ans, 3-5K€ par pari)</div>
  {lt_cards}
</div>

<!-- MACRO + DRIVERS -->
<div style="background:#fff;padding:16px 24px;border-bottom:1px solid #eee;display:flex;gap:20px;flex-wrap:wrap">
  <div style="flex:1;min-width:200px">
    <div style="font-size:12px;font-weight:700;color:#888;letter-spacing:.05em;margin-bottom:10px">MACRO</div>
    <table style="width:100%;border-collapse:collapse">
      <thead><tr style="border-bottom:1px solid #eee">
        <th style="padding:5px 8px;text-align:left;font-size:10px;color:#888">Indicateur</th>
        <th style="padding:5px 8px;text-align:right;font-size:10px;color:#888">Niveau</th>
        <th style="padding:5px 8px;text-align:right;font-size:10px;color:#888">Sem.</th>
      </tr></thead>
      <tbody>{macro_rows}</tbody>
    </table>
  </div>
  <div style="flex:1;min-width:200px">
    <div style="font-size:12px;font-weight:700;color:#888;letter-spacing:.05em;margin-bottom:10px">DRIVERS MACRO</div>
    <table style="width:100%;border-collapse:collapse">
      <tbody>{driver_rows}</tbody>
    </table>
  </div>
</div>

<!-- COMMENTAIRE -->
<div style="background:#161616;border-radius:0 0 12px 12px;padding:20px 24px">
  <div style="font-size:11px;font-weight:600;color:#555;letter-spacing:.05em;margin-bottom:10px">COMMENTAIRE DU DESK</div>
  <div style="color:#ccc;font-size:13px;line-height:1.9;white-space:pre-line">{a.get('commentaire_weekend','')}</div>
  <div style="margin-top:16px;padding-top:12px;border-top:1px solid #2a2a2a;color:#555;font-size:10px">
    Pascal Terminal v2 · {gen_at} · {data.get('screened_count',0)} instruments scannés ·
    Hit rate: {bt.get('hit_rate','N/A')}% ·
    <em>Document informatif — ne constitue pas un conseil en investissement</em>
  </div>
</div>

</div></body></html>"""
    return html


def send_email(html: str, subject: str):
    sender   = os.environ["EMAIL_SENDER"]
    recipient= os.environ["EMAIL_RECIPIENT"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = recipient
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(sender, password)
        s.sendmail(sender, recipient, msg.as_string())
    print(f"Email envoyé à {recipient}")


def generate_and_send(data: dict):
    week = data.get("week_number","")
    date = data.get("date", datetime.date.today().isoformat())
    subject = f"Pascal Terminal · Samedi S{week} · {date}"
    html = build_html_email(data)

    output = os.path.join(os.path.dirname(__file__), "..", "dashboard", "latest_email.html")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        f.write(html)

    try:
        send_email(html, subject)
    except Exception as e:
        print(f"Email non envoyé (variables d'env manquantes?) : {e}")

    return html
