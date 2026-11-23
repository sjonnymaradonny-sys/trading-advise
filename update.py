#!/usr/bin/env python3
"""Haalt automatisch koersen op voor 9 markten en bouwt index.html met KOPEN/HOUDEN/VERKOPEN.
Geen extra pakketten nodig. Gebruik:  python update.py"""
import json, urllib.request, datetime

MARKETS = [  # (naam, Yahoo-ticker)
    ("Bitcoin", "BTC-USD"), ("Vanguard FTSE All-World (VWCE)", "VWCE.DE"),
    ("Goud", "GC=F"), ("Vertiv", "VRT"), ("Arista Networks", "ANET"),
    ("Nike", "NKE"), ("iShares MSCI World (IWDA)", "IWDA.AS"),
    ("Invesco QQQ", "QQQ"), ("Nvidia", "NVDA"),
]

def fetch(sym):
    now = int(datetime.datetime.now().timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1=0&period2={now}&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.load(r)["chart"]["result"][0]
    pairs = [(t, c) for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]) if c is not None]
    closes = [c for _, c in pairs]
    since = datetime.datetime.fromtimestamp(pairs[0][0]).strftime("%m-%Y")
    return closes, res["meta"].get("currency", ""), since

def sma(a, n):
    return sum(a[-n:]) / n if len(a) >= n else None

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
    sig = "buy" if score >= 2 else "sell" if score <= -2 else "hold"
    return sig, " · ".join(why)

rows = []
for name, sym in MARKETS:
    try:
        closes, cur, since = fetch(sym)
        sig, why = analyse(closes)
        rows.append(dict(name=name, sym=sym, sig=sig, why=why, price=round(closes[-1], 2), cur=cur, since=since, n=len(closes)))
    except Exception as e:
        rows.append(dict(name=name, sym=sym, sig="none", why=f"Fout bij ophalen: {e}", price=None, cur="", since="", n=0))
        print("FOUT", sym, e)

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
</style></head><body><main><h1>Mijn Trading Signalen</h1>
<div class="mu" id="s"></div><div id="l"></div>
<p class="mu">Automatisch berekend uit dagkoersen (trend + RSI). Geen financieel advies; beslis altijd zelf.</p></main>
<script>
const D=__DATA__,T={buy:"KOPEN / BIJKOPEN",sell:"VERKOPEN / VERMINDEREN",hold:"HOUDEN / WACHTEN",none:"Geen data"};
document.getElementById("s").textContent="Laatst bijgewerkt: "+D.stamp;
const l=document.getElementById("l");
D.rows.forEach(r=>{const c=document.createElement("div");c.className="card";
const w=document.createElement("div");w.className="row";
const a=document.createElement("div");const n=document.createElement("div");n.className="n";n.textContent=r.name;
const t=document.createElement("div");t.className="mu";t.textContent=r.sym+(r.price?" · "+r.price+" "+r.cur+" · data sinds "+r.since+" ("+r.n+" dagen)":"");
a.append(n,t);const b=document.createElement("span");b.className="b "+r.sig;b.textContent=T[r.sig];
w.append(a,b);const y=document.createElement("p");y.className="mu";y.textContent=r.why;c.append(w,y);l.append(c)});
</script></body></html>"""

open("index.html", "w", encoding="utf-8").write(HTML.replace("__DATA__", data))
print("index.html bijgewerkt", stamp)
