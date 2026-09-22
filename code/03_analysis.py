"""Part 4: charts, decomposition, early vs late returns, bond risk, Checkpoint 4."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

T = 46
res = pd.read_csv("output/cohort_results.csv", index_col="start")
paths = pd.read_pickle("output/paths.pkl")
df = pd.read_csv("data/returns_1945_2024_both_cpi_defs.csv", index_col="year")
eq, bd = df["sp500_real_dec"], df["tbond_real_dec"]
C_EQ, C_GP, C3 = "#2a6fdb", "#e07b39", "#555555"
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.3})

# 4.1(1) terminal wealth by cohort
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(res.index, res.W_eq, "-o", ms=3.5, color=C_EQ, label="100% equities")
ax.plot(res.index, res.W_gp, "-o", ms=3.5, color=C_GP, label="Glide path (90%→20% equity)")
ax.axhline(58.05, ls=":", color=C3, lw=1); ax.text(1945, 66, "Total contributions (58.05)", fontsize=8, color=C3)
ax.set(xlabel="Cohort start year (retires 46 years later)",
       ylabel="Terminal real wealth (first-year contribution = $1)",
       title="Terminal real wealth at retirement, by cohort")
ax.legend(frameon=False); fig.tight_layout(); fig.savefig("output/fig1_terminal_wealth.png"); plt.close()

# 4.1(2) best / median / worst
def pick(W, g):
    s = res[W]; med_start = (s - s.median()).abs().idxmin()
    return {lab: (st, res.loc[st, W], res.loc[st, g]) for lab, st in
            [("Worst", s.idxmin()), ("Median", med_start), ("Best", s.idxmax())]}
pe, pg = pick("W_eq", "irr_eq"), pick("W_gp", "irr_gp")
tab = pd.DataFrame([[lab, "Equities", *pe[lab]] for lab in pe] + [[lab, "Glide path", *pg[lab]] for lab in pg],
                   columns=["Outcome", "Strategy", "Start", "W", "IRR"])
tab["Retire"] = tab.Start + T
print("=== Best / median / worst (median = cohort closest to median; 35 cohorts so it is exact) ===")
print(tab.assign(W=tab.W.round(0).astype(int), IRR=(100 * tab.IRR).round(2)).to_string(index=False))
fig, ax = plt.subplots(figsize=(8, 4.6)); x = np.arange(3); wdt = 0.38
for j, (p, col, lab) in enumerate([(pe, C_EQ, "100% equities"), (pg, C_GP, "Glide path")]):
    vals = [p[o][1] for o in ["Worst", "Median", "Best"]]
    bars = ax.bar(x + (j - 0.5) * wdt, vals, wdt, color=col, label=lab)
    for b_, o in zip(bars, ["Worst", "Median", "Best"]):
        st, Wv, g = p[o]
        ax.text(b_.get_x() + b_.get_width() / 2, Wv + 8, f"${Wv:.0f}\nIRR {g:.2%}\n{st}→{st+T}",
                ha="center", fontsize=7.5)
ax.set_xticks(x, ["Worst cohort", "Median cohort", "Best cohort"]); ax.set_ylim(0, 720)
ax.set(ylabel="Terminal real wealth", title="Best, median and worst cohorts by strategy")
ax.legend(frameon=False, loc="upper left"); fig.tight_layout(); fig.savefig("output/fig2_best_median_worst.png"); plt.close()

# 4.1(3) equity / glide ratio
ratio = res.W_eq / res.W_gp
fig, ax = plt.subplots(figsize=(9, 4.2))
ax.plot(ratio.index, ratio, "-o", ms=3.5, color=C3); ax.axhline(1, color="k", lw=0.8)
ax.set(xlabel="Cohort start year", ylabel="W(equities) / W(glide path)",
       title="Terminal wealth under equities relative to glide path (the \"cost of insurance\")")
fig.tight_layout(); fig.savefig("output/fig3_equity_to_glide_ratio.png"); plt.close()
print(f"\nEquity/glide ratio: min {ratio.min():.2f} ({ratio.idxmin()}), max {ratio.max():.2f} ({ratio.idxmax()}), "
      f"median {ratio.median():.2f}; cohorts with ratio<1: {list(ratio[ratio < 1].index)}")

# 4.2 decomposition best vs worst equity cohort
b, w = res.W_eq.idxmax(), res.W_eq.idxmin()
fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 7.5), sharex=True)
for s, col, lab in [(b, C_EQ, "Best"), (w, "#c0392b", "Worst")]:
    a1.plot(np.arange(T + 1) + 22, paths[s]["eq"], color=col, lw=2, label=f"{lab}: starts {s}, retires {s+T}")
    a2.bar(np.arange(T) + 22 + (0.2 if lab == "Worst" else -0.2), 100 * paths[s]["r_eq"], 0.4, color=col,
           label=f"{lab} ({s}–{s+T-1})")
a1.set(ylabel="Portfolio value (real)", title="100% equities: best vs worst cohort")
a1.legend(frameon=False)
a2.axhline(0, color="k", lw=0.8); a2.axvspan(57.5, 67.5, color="grey", alpha=0.12)
a2.text(58.3, 45, "last 10 years", fontsize=8)
a2.set(xlabel="Age (top: value at end of year; bottom: return earned during year at that age)", ylabel="Real S&P 500 return (%)")
a2.legend(frameon=False, fontsize=8); fig.tight_layout(); fig.savefig("output/fig4_best_vs_worst_decomposition.png"); plt.close()
for s in (b, w):
    r = paths[s]["r_eq"]
    print(f"Cohort {s}: first-10 avg {r[:10].mean():.2%}, last-10 avg {r[-10:].mean():.2%}, "
          f"final-year return ({s+T-1}) {r[-1]:.2%}, W at age 58 {paths[s]['eq'][36]:.0f}, final {paths[s]['eq'][-1]:.0f}")

# 4.3 early vs late returns
print("\n=== 4.3 Early vs late returns (35 overlapping cohorts) ===")
for W_, pre, lab in [("W_eq", "avg_eq", "Equities  (vs avg real equity return)"),
                     ("W_gp", "avg_eq", "Glide path(vs avg real equity return)"),
                     ("W_gp", "avg_gp", "Glide path(vs avg glide portfolio return)")]:
    for win in ["first10", "last10"]:
        rho = np.corrcoef(res[W_], res[f"{pre}_{win}"])[0, 1]
        print(f"{lab:42s} {win:7s}: corr = {rho:+.3f}, R^2 = {rho**2:.3f}")
bd_career = pd.Series([bd.loc[s:s + T - 1].mean() for s in res.index], index=res.index)
print(f"Glide path vs career-average real bond return: corr = {np.corrcoef(res.W_gp, bd_career)[0,1]:+.3f}")

# 4.4 bond risk
print("\n=== 4.4 Bond risk ===")
neg = bd[bd < 0]
print(f"Years with negative real bond return: {len(neg)} of {len(bd)} ({len(neg)/len(bd):.1%})")
print(f"Worst real bond year: {bd.idxmin()} {bd.min():.2%}")
print(f"2022 real: S&P {eq[2022]:.2%}, 10y T-bond {bd[2022]:.2%}")
both_neg = df.index[(eq < 0) & (bd < 0)]
print(f"Years with both real stock & bond returns negative: {list(both_neg)}")
roll = eq.rolling(10).corr(bd).dropna()
print(f"Rolling 10-yr windows: {len(roll)} (first ends {roll.index[0]}, last ends {roll.index[-1]}); "
      f"positive {int((roll > 0).sum())}, negative {int((roll < 0).sum())}; min {roll.min():.2f} ({roll.idxmin()}), "
      f"max {roll.max():.2f} ({roll.idxmax()})")
print(f"Full-sample stock-bond real corr: {eq.corr(bd):.3f}")
fig, ax = plt.subplots(figsize=(9, 4))
ax.plot(roll.index, roll, color=C3); ax.axhline(0, color="k", lw=0.8)
ax.fill_between(roll.index, roll, 0, where=roll > 0, color=C_GP, alpha=0.3, label="positive")
ax.fill_between(roll.index, roll, 0, where=roll < 0, color=C_EQ, alpha=0.3, label="negative")
ax.set(xlabel="Window end year", ylabel="Correlation", title="Rolling 10-year correlation, real S&P 500 vs real 10-yr Treasury returns")
ax.legend(frameon=False); fig.tight_layout(); fig.savefig("output/fig5_rolling_stock_bond_corr.png"); plt.close()
roll.to_csv("output/rolling_corr.csv")

# Checkpoint 4
print("\n=== CHECKPOINT 4 ===")
print(f"Best eq cohort {b}: returns end {b+T-1}; real S&P {b+T-5}-{b+T-1}: "
      + ", ".join(f"{eq[y]:.1%}" for y in range(b + T - 5, b + T)))
print(f"Worst eq cohort {w}: returns end {w+T-1}; real S&P {w+T-5}-{w+T-1}: "
      + ", ".join(f"{eq[y]:.1%}" for y in range(w + T - 5, w + T)))
print(f"Best/worst: equities {res.W_eq.max()/res.W_eq.min():.2f} vs glide {res.W_gp.max()/res.W_gp.min():.2f} -> reduced: "
      f"{res.W_gp.max()/res.W_gp.min() < res.W_eq.max()/res.W_eq.min()}")
print(f"Median: glide {res.W_gp.median():.0f} < equities {res.W_eq.median():.0f}: {res.W_gp.median() < res.W_eq.median()}")
print(f"2022 both negative: {eq[2022] < 0 and bd[2022] < 0}")
