"""Parts 2-4: accumulation model, cohort simulation, analysis.

Timing convention: contribution c_k is made at the START of working year k and
earns that year's full return: W_{k+1} = (W_k + c_k)(1 + r_k).  Terminal wealth
W_46 is measured at the end of the 46th working year (= start of retirement).
All values are real, in units of the cohort's first-year contribution ($1).
Inflation: CPI-U Dec/Dec (FRED CPIAUCNS).
"""
import numpy as np
import pandas as pd
from scipy.optimize import brentq

T = 46                                   # ages 22..67 contribute; retire at 68
df = pd.read_csv("data/returns_1945_2024_both_cpi_defs.csv", index_col="year")
eq = df["sp500_real_dec"]; bd = df["tbond_real_dec"]
k = np.arange(T)
c = 1.01 ** k                            # real contributions
alpha = 0.90 - 0.70 / 45 * k             # glide-path equity weight

def simulate(r):
    """Return path W_0..W_T for returns r (len T)."""
    W = np.zeros(T + 1)
    for i in range(T):
        W[i + 1] = (W[i] + c[i]) * (1 + r[i])
    return W

def irr(WT):
    """g solving sum_k c_k (1+g)^(T-k) = W_T."""
    f = lambda g: np.sum(c * (1 + g) ** (T - k)) - WT
    return brentq(f, -0.5, 0.5)

# ---------------- Checkpoint 2 ------------------------------------------------
print("=== CHECKPOINT 2 ===")
for age in (22, 45, 68):
    kk = min(age - 22, 45)
    print(f"alpha at age {age} (k={kk}): {alpha[kk]:.2%}")
print("  (age 68 = retirement date; last allocation year is k=45, age 67, alpha=20%)")
print(f"Total real contributions sum_k 1.01^k = {c.sum():.4f}")
r45 = eq.loc[1945:1945 + T - 1].values
W = simulate(r45)
print("\nHand check, 1945 cohort, 100% equities:")
w = 0.0
for i in range(3):
    y = 1945 + i
    new = (w + c[i]) * (1 + r45[i])
    print(f"  k={i} ({y}): ({w:.6f} + {c[i]:.6f}) x (1 + {r45[i]:.6f}) = {new:.6f}   [sim: {W[i+1]:.6f}]")
    w = new
print(f"1945 cohort terminal wealth (equities): {W[-1]:.2f}")

# ---------------- Part 3 ------------------------------------------------------
first, last_data = eq.index.min(), eq.index.max()
starts = range(first, last_data - (T - 1) + 1)
print(f"\n=== COHORTS: {len(starts)} cohorts; first {starts[0]} (returns {starts[0]}-{starts[0]+T-1}, "
      f"retire {starts[0]+T}), last {starts[-1]} (returns {starts[-1]}-{starts[-1]+T-1}, retire {starts[-1]+T})")

rows, paths = [], {}
for s in starts:
    yrs = range(s, s + T)
    re, rb = eq.loc[yrs].values, bd.loc[yrs].values
    rg = alpha * re + (1 - alpha) * rb
    We, Wg = simulate(re), simulate(rg)
    paths[s] = dict(eq=We, gp=Wg, r_eq=re)
    rows.append(dict(start=s, retire=s + T, W_eq=We[-1], W_gp=Wg[-1],
                     irr_eq=irr(We[-1]), irr_gp=irr(Wg[-1]),
                     ratio_eq=We[-1] / c.sum(), ratio_gp=Wg[-1] / c.sum(),
                     avg_eq_first10=re[:10].mean(), avg_eq_last10=re[-10:].mean(),
                     avg_gp_first10=rg[:10].mean(), avg_gp_last10=rg[-10:].mean()))
res = pd.DataFrame(rows).set_index("start")
res.to_csv("output/cohort_results.csv")
pd.to_pickle(paths, "output/paths.pkl")

print("\n=== CHECKPOINT 3: all cohorts ===")
show = pd.DataFrame({
    "Retire": res.retire,
    "W equity": res.W_eq.round(0).astype(int),
    "W glide": res.W_gp.round(0).astype(int),
    "IRR eq %": (100 * res.irr_eq).round(2),
    "IRR gp %": (100 * res.irr_gp).round(2),
    "W/C eq": res.ratio_eq.round(2),
    "W/C gp": res.ratio_gp.round(2)})
print(show.to_string())
for lab, W_, g_ in [("EQUITIES", "W_eq", "irr_eq"), ("GLIDE PATH", "W_gp", "irr_gp")]:
    b, w_ = res[W_].idxmax(), res[W_].idxmin()
    print(f"\n{lab}: best  start {b} retire {b+T}  W={res.loc[b,W_]:.0f}  IRR={res.loc[b,g_]:.2%}")
    print(f"{lab}: worst start {w_} retire {w_+T}  W={res.loc[w_,W_]:.0f}  IRR={res.loc[w_,g_]:.2%}")
    print(f"{lab}: best/worst = {res[W_].max()/res[W_].min():.2f}   median W = {res[W_].median():.0f}"
          f"   median IRR = {res[g_].median():.2%}")
