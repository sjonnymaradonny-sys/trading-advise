#!/usr/bin/env python3
"""Haalt koersen op (volledige historie), berekent signalen en bouwt index.html
met portefeuille + actieplan voor DEGIRO (België). Geen extra pakketten nodig."""
import json, urllib.request, datetime

# naam, signaal-ticker (lange historie), handel-ticker (wat je op DEGIRO koopt), soort, orderkosten EUR, beurstaks %, opmerking
MARKETS = [
 ("Bitcoin","BTC-USD","BTCE.DE","etc",3,0.35,"Je koopt geen echte bitcoin op DEGIRO, enkel een bitcoin-ETP. Controleer of die voor jou beschikbaar is."),
 ("Vanguard FTSE All-World (VWCE)","VWCE.DE","VWCE.DE","etf",3,1.32,"Accumulerend fonds: beurstaks 1,32%. Via Tradegate (Kernselectie) vaak maar 1 euro orderkost."),
 ("Goud","GC=F","4GLD.DE","etc",3,0.35,"Je koopt goud via een goud-ETC (bv. Xetra-Gold), niet via futures."),
 ("Vertiv","VRT","VRT","stock",2,0.35,"Amerikaans aandeel: wisselkost ca. 0,25%. Geen fracties, je koopt hele aandelen."),
 ("Arista Networks","ANET","ANET","stock",2,0.35,"Amerikaans aandeel: wisselkost ca. 0,25%. Geen fracties."),
 ("Nike","NKE","NKE","stock",2,0.35,"Amerikaans aandeel: wisselkost ca. 0,25%. Geen fracties."),
 ("iShares MSCI World (IWDA)","IWDA.AS","IWDA.AS","etf",3,1.32,"Accumulerend fonds: beurstaks 1,32%. Lijkt sterk op VWCE (veel overlap)."),
 ("Invesco QQQ (Nasdaq-100)","QQQ","EQQQ.DE","etf",3,0.12,"QQQ zelf is een Amerikaanse ETF die Europese particulieren niet kunnen kopen. Gebruik de Europese versie (EQQQ)."),
 ("Nvidia","NVDA","NVDA","stock",2,0.35,"Amerikaans aandeel: wisselkost ca. 0,25%. Geen fracties."),
]

def fetch(sym, short=False):
    now = int(datetime.datetime.now().timestamp())
    q = "range=5d&interval=1d" if short else f"period1=0&period2={now}&interval=1d"
    req = urllib.request.Request(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?{q}", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.load(r)["chart"]["result"][0]
    pairs = [(t, c) for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]) if c is not None]
    return [c for _, c in pairs], res["meta"].get("currency", ""), datetime.datetime.fromtimestamp(pairs[0][0]).strftime("%m-%Y")

def sma(a, n): return sum(a[-n:]) / n if len(a) >= n else None

def rsi(a, n=14):
    if len(a) < n + 1: return None
    g = l = 0.0
    for i in range(len(a) - n, len(a)):
        d = a[i] - a[i - 1]
        if d > 0: g += d
        else: l -= d
    return 100.0 if l == 0 else 100 - 100 / (1 + g / l)

def analyse(a):
    p = a[-1]; s50, s200, r = sma(a, 50), sma(a, 200), rsi(a)
    score, why = 0, []
    if p > s50: score += 1; why.append("koers boven 50-daags gemiddelde")
    else: score -= 1; why.append("koers onder 50-daags gemiddelde")
    if s200:
        if s50 > s200: score += 1; why.append("50d boven 200d (opwaartse trend)")
        else: score -= 1; why.append("50d onder 200d (neerwaartse trend)")
    if r is not None:
        if r < 30: score += 1; why.append(f"RSI {r:.0f} (oversold)")
        elif r > 70: score -= 1; why.append(f"RSI {r:.0f} (overbought)")
        else: why.append(f"RSI {r:.0f} (neutraal)")
    return ("buy" if score >= 2 else "sell" if score <= -2 else "hold"), score, " · ".join(why)

try: fx = fetch("EURUSD=X", True)[0][-1]
except Exception as e: fx = None; print("FOUT wisselkoers", e)

def to_eur(p, cur):
    if cur == "EUR": return p
    if cur == "USD" and fx: return p / fx
    return None

rows = []
for name, sym, tsym, kind, fee, tob, note in MARKETS:
    row = dict(name=name, sym=sym, tsym=tsym, kind=kind, fee=fee, tob=tob, note=note, fx=False,
               sig="none", score=0, why="", price=None, cur="", since="", n=0, price_eur=None)
    try:
        closes, cur, since = fetch(sym)
        sig, score, why = analyse(closes)
        row.update(sig=sig, score=score, why=why, price=round(closes[-1], 2), cur=cur, since=since, n=len(closes))
    except Exception as e:
        row["why"] = f"Fout bij ophalen: {e}"; print("FOUT", sym, e)
    try:
        tp, tcur, _ = fetch(tsym, True)
        pe = to_eur(tp[-1], tcur)
        if pe: row.update(price_eur=round(pe, 2), fx=(tcur == "USD"))
    except Exception as e:
        print("FOUT handelsprijs", tsym, e)
    rows.append(row)

stamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
data = json.dumps(dict(rows=rows, stamp=stamp)).replace("<", "\\u003c")

HTML = """<!DOCTYPE html><html lang="nl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Mijn Trading Signalen</title>
<style>
:root{--bg:#f6f7f9;--c:#fff;--tx:#14181f;--mu:#667085;--bd:#e3e6eb;--g:#12805c;--gb:#e3f6ee;--r:#c0392b;--rb:#fdeceb;--y:#8a6d00;--yb:#fff6d6}
@media(prefers-color-scheme:dark){:root{--bg:#0f1318;--c:#181d25;--tx:#eef1f5;--mu:#9aa4b2;--bd:#2a313c;--g:#4fd1a0;--gb:#123327;--r:#ff8a7d;--rb:#3a1c19;--y:#f2cc4d;--yb:#3a3213}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:16px/1.5 system-ui,sans-serif}
main{max-width:760px;margin:0 auto;padding:20px 16px 40px}h1{margin:0 0 4px;font-size:1.5rem}
.mu{color:var(--mu);font-size:.9rem}.card{background:var(--c);border:1px solid var(--bd);border-radius:14px;padding:16px;margin:12px 0}
.row{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}.n{font-weight:650}
.b{padding:6px 14px;border-radius:999px;font-weight:700}.buy{background:var(--gb);color:var(--g)}
.sell{background:var(--rb);color:var(--r)}.hold{background:var(--yb);color:var(--y)}.none{background:var(--bd);color:var(--mu)}
input{width:130px;margin:6px 0;padding:8px 10px;border:1px solid var(--bd);border-radius:10px;background:var(--bg);color:var(--tx);font:inherit}
.a{padding:8px 0;border-top:1px solid var(--bd)}.a:first-of-type{border-top:0}
</style></head><body><main><h1>Mijn Trading Signalen</h1>
<div class="mu" id="s"></div><div id="app"></div>
<p class="mu">Automatisch berekend uit dagkoersen (trend + RSI). Kosten en beurstaks zijn schattingen: controleer altijd de "geschatte kosten" in DEGIRO voor je bevestigt. Geen financieel advies; beslis altijd zelf. Je invoer blijft enkel in deze browser bewaard.</p></main>
<script>
const D=__DATA__,K="portf_v1",T={buy:"KOPEN",sell:"VERKOPEN",hold:"HOUDEN",none:"Geen data"};
let S={cash:600,h:{}};
try{Object.assign(S,JSON.parse(localStorage.getItem(K)||"{}"))}catch(e){}
const save=()=>{try{localStorage.setItem(K,JSON.stringify(S))}catch(e){}};
const E=v=>"\\u20ac"+v.toFixed(2);
const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e};
const cost=(r,v)=>r.fee+v*r.tob/100+(r.fx?v*0.0025:0);
const unit=r=>r.price_eur*(1+r.tob/100+(r.fx?0.0025:0));
document.getElementById("s").textContent="Laatst bijgewerkt: "+D.stamp;
const app=document.getElementById("app");
const cc=el("div","card");cc.append(el("div","n","Mijn geld"),el("div","mu","Bedrag (in euro) dat nu vrij staat om te beleggen, zonder wat je al belegd hebt:"));
const ci=el("input");ci.type="number";ci.min=0;ci.value=S.cash;ci.oninput=()=>{S.cash=Math.max(0,parseFloat(ci.value)||0);save();upd()};cc.append(ci);
const pc=el("div","card");app.append(cc,pc);
const hv={};
D.rows.forEach(r=>{const c=el("div","card"),w=el("div","row"),a=el("div");
a.append(el("div","n",r.name),el("div","mu",r.tsym+" (signaal: "+r.sym+")"+(r.price_eur?" \\u00b7 prijs "+E(r.price_eur):"")+(r.since?" \\u00b7 data sinds "+r.since+" ("+r.n+" dagen)":"")));
w.append(a,el("span","b "+r.sig,T[r.sig]));c.append(w,el("p","mu",r.why));
if(r.note)c.append(el("p","mu","Let op: "+r.note));
c.append(el("span","mu","Ik heb (aantal stuks): "));
const i=el("input");i.type="number";i.min=0;i.value=S.h[r.sym]||"";i.placeholder="0";
i.oninput=()=>{S.h[r.sym]=Math.max(0,parseInt(i.value)||0);save();upd()};
hv[r.sym]=el("div","mu");c.append(i,hv[r.sym]);app.append(c)});
function upd(){
 let cash=S.cash,out=[],tc=0,pv=0;
 D.rows.forEach(r=>{const n=S.h[r.sym]||0;if(r.price_eur)pv+=n*r.price_eur});
 D.rows.forEach(r=>{const n=S.h[r.sym]||0;
  hv[r.sym].textContent=n&&r.price_eur?"Ingezet: "+n+" stuk(ken) \\u2248 "+E(n*r.price_eur)+" ("+(100*n*r.price_eur/(pv+S.cash||1)).toFixed(0)+"% van mijn totaal)":"";
  if(r.sig==="sell"&&n>0&&r.price_eur){const v=n*r.price_eur,c=cost(r,v);cash+=v-c;tc+=c;out.push("VERKOOP alle "+n+" stuk(ken) "+r.name+" \\u2248 "+E(v)+" (kosten \\u2248 "+E(c)+")")}});
 let cand=D.rows.filter(r=>r.sig==="buy"&&r.price_eur).sort((a,b)=>b.score-a.score);
 const skipped=cand.slice(Math.max(1,Math.floor(cash/150)));cand=cand.slice(0,Math.max(1,Math.floor(cash/150)));
 const b={};cand.forEach(r=>b[r.sym]=0);
 const per=cand.length?cash/cand.length:0;
 cand.forEach(r=>{const n=Math.floor((per-r.fee)/unit(r));if(n>0){b[r.sym]=n;cash-=n*unit(r)+r.fee}});
 for(;;){const o=cand.filter(r=>cash>=unit(r)+(b[r.sym]?0:r.fee)).sort((x,y)=>unit(x)-unit(y))[0];if(!o)break;cash-=unit(o)+(b[o.sym]?0:o.fee);b[o.sym]++}
 cand.forEach(r=>{const n=b[r.sym];if(n>0){const v=n*r.price_eur,c=cost(r,v);tc+=c;out.push("KOOP "+n+" \\u00d7 "+r.name+" \\u2248 "+E(v)+" (kosten \\u2248 "+E(c)+", "+(100*c/v).toFixed(1)+"%)")}
  else out.push(r.name+": signaal KOPEN, maar 1 stuk kost \\u2248 "+E(unit(r)+r.fee)+" en past niet in je budget per positie.")});
 skipped.forEach(r=>out.push(r.name+": ook KOPEN, maar met je budget houd je het beter bij minder posities (kosten blijven laag)."));
 D.rows.filter(r=>r.sig==="buy"&&!r.price_eur).forEach(r=>out.push(r.name+": prijs onbekend, kan niet berekend worden."));
 D.rows.filter(r=>r.sig==="hold"&&(S.h[r.sym]||0)>0).forEach(r=>out.push("HOUD "+r.name+" aan, nu niets doen."));
 pc.replaceChildren(el("div","n","Wat moet ik nu doen?"));
 if(!out.length)pc.append(el("div","a","Niets doen: er is geen koop- of verkoopsignaal dat past bij je budget."));
 out.forEach(x=>pc.append(el("div","a",x)));
 const tot=pv+S.cash;
 pc.append(el("p","mu","Totale kosten van dit plan \\u2248 "+E(tc)+" \\u00b7 blijft over in cash \\u2248 "+E(cash)+" \\u00b7 mijn totaal nu \\u2248 "+E(tot)+"."));
 if(tot>0&&tc/tot>0.02)pc.append(el("p","mu","Let op: de kosten zijn meer dan 2% van je totaal. Bij kleine bedragen eet dat een groot deel van je winst op. Weinig en groter handelen is goedkoper dan vaak en klein."));
}
upd();
</script></body></html>"""

open("index.html", "w", encoding="utf-8").write(HTML.replace("__DATA__", data))
print("index.html bijgewerkt", stamp)
