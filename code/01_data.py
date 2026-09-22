"""Part 1: download Damodaran returns + FRED CPI-U, compute real returns.

Sources
- Damodaran, histretSP.html (NYU Stern): S&P 500 total return (incl. dividends),
  US T-Bond (10-year) total return, both nominal, annual.
- FRED CPIAUCNS (CPI-U, all items, U.S. city average, not seasonally adjusted).
  Inflation for year t is computed two ways (Dec/Dec and annual-average) so the
  choice can be made explicitly; see INFLATION_DEF.
"""
import io, sys, requests
import numpy as np
import pandas as pd
import pandas_datareader.data as web

START, END = 1945, 2024
URL = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histretSP.html"

# --- Damodaran --------------------------------------------------------------
html = requests.get(URL, timeout=60, headers={"User-Agent": "Mozilla/5.0"}).text
open("data/histretSP.html", "w", encoding="utf-8").write(html)
raw = pd.read_html(io.StringIO(html))[0]
raw = raw.iloc[2:, [0, 1, 4]]
raw.columns = ["year", "sp500_nom", "tbond_nom"]
raw = raw[pd.to_numeric(raw["year"], errors="coerce").notna()].copy()
raw["year"] = raw["year"].astype(int)
for c in ["sp500_nom", "tbond_nom"]:
    raw[c] = raw[c].astype(str).str.replace("%", "").str.strip().astype(float) / 100
dam = raw.set_index("year").loc[START:END]

# --- FRED CPI-U -------------------------------------------------------------
cpi = web.DataReader("CPIAUCNS", "fred", f"{START-1}-01-01", f"{END}-12-31")["CPIAUCNS"]
cpi.to_csv("data/fred_CPIAUCNS_monthly.csv")
dec = cpi[cpi.index.month == 12]; dec.index = dec.index.year
avg = cpi.groupby(cpi.index.year).mean()
infl = pd.DataFrame({"infl_dec": dec.pct_change(), "infl_avg": avg.pct_change()}).loc[START:END]

df = dam.join(infl)
for d in ["dec", "avg"]:
    df[f"sp500_real_{d}"] = (1 + df.sp500_nom) / (1 + df[f"infl_{d}"]) - 1
    df[f"tbond_real_{d}"] = (1 + df.tbond_nom) / (1 + df[f"infl_{d}"]) - 1
df.index.name = "year"
df.to_csv("data/returns_1945_2024_both_cpi_defs.csv")

gm = lambda s: np.exp(np.log1p(s).mean()) - 1
print("N years:", df.sp500_nom.notna().sum(), df.tbond_nom.notna().sum(),
      df.infl_dec.notna().sum(), df.infl_avg.notna().sum())
for d in ["dec", "avg"]:
    print(f"\n=== inflation definition: {d} ===")
    print(f"GM real S&P : {gm(df[f'sp500_real_{d}']):.4%}")
    print(f"GM real bond: {gm(df[f'tbond_real_{d}']):.4%}")
    s, b = df[f"sp500_real_{d}"], df[f"tbond_real_{d}"]
    print(f"Worst S&P  : {s.idxmin()} {s.min():.2%}")
    print(f"Worst bond : {b.idxmin()} {b.min():.2%}")
    print(f"2008 S&P   : {s[2008]:.2%}   2022 S&P: {s[2022]:.2%}   2022 bond: {b[2022]:.2%}")
print(f"\nNominal GM S&P {gm(df.sp500_nom):.4%}, bond {gm(df.tbond_nom):.4%}")
print(df.loc[[2008, 2022], ["sp500_nom", "tbond_nom", "infl_dec", "infl_avg"]])
