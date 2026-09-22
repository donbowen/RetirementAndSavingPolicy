# Comparison with the `claude-long-prompt` branch

This compares this branch (`claude-sept-2026`, [RESULTS.md](RESULTS.md)) with `origin/claude-long-prompt` (`summary_findings.txt`, `claude_code_working_log.md`, `cohort_results.csv`, `simulation.py`).

## Bottom line
Both runs use the same model. The only difference in method is **how annual inflation is measured**. When I rerun this branch's code with the other branch's inflation measure, I reproduce **all 35 of its cohort results for both strategies exactly** (every terminal-wealth value matches after rounding to the dollar), and its real return series matches mine exactly. Neither run has a coding error.

The two branches reach the same qualitative answers. They differ in (a) how they handled a checkpoint that conflicted with itself, and (b) a few interpretive claims in `summary_findings.txt` that the data do not support.

## 1. Method differences

| | This branch | `claude-long-prompt` |
|---|---|---|
| Data sources | Damodaran + FRED `CPIAUCNS` | Same |
| Inflation measure | **December to December** | **Annual average** of monthly CPI |
| Timing, contributions, glide path, IRR | Start-of-year contribution; c<sub>k</sub> = 1.01<sup>k</sup>; α<sub>k</sub> = 0.90 − (0.70/45)k; IRR with `brentq` | Same |
| Cohorts | 35 (1945–1979) | 35 (1945–1979) |

Dec/Dec inflation covers the same January–December window as Damodaran's calendar-year returns. Annual-average inflation compares the average price level of year *t* with that of year *t−1*, so it runs about six months behind the return window. This matters most in years when inflation changed quickly: 2008 (0.1% Dec/Dec vs. 3.8% annual average) and 2022 (6.5% vs. 8.0%).

## 2. How each run handled the conflicting checkpoint
Checkpoint 1 expects 2008 at about −36% and 2022 at about −24.5% (real S&P 500). No single inflation measure delivers both.

| | Dec/Dec (this branch) | Annual average (other branch) |
|---|---|---|
| 2008 real S&P 500 (target ≈ −36%) | −36.61% ✅ | −38.90% ❌ |
| 2022 real S&P 500 (target ≈ −24.5%) | −23.01% ⚠️ | −24.11% ✅ |

- **This branch** found the conflict, stopped, and asked the user which measure to use. It chose Dec/Dec and recorded the 2022 miss.
- **`claude-long-prompt`** marked **both** as passing (✓), including 2008 at −38.90% against a target of about −36%. That is roughly 3 percentage points off, a miss the README's "stop and debug" instruction was meant to catch. The same thing appears in its Checkpoint 4 ("2008: −38.9% ✓").

## 3. Headline numbers side by side

| Result | This branch (Dec/Dec) | `claude-long-prompt` (annual avg) |
|---|---|---|
| Geometric mean real return, S&P 500 / 10-yr bond | 7.53% / 1.07% | 7.53% / 1.06% |
| Best equity cohort | 1954→2000: 607 (IRR 8.57%) | 1954→2000: 604 (IRR 8.55%) |
| Worst equity cohort | 1963→2009: 210 (IRR 5.07%) | 1963→2009: 201 (IRR 4.91%) |
| Best/worst, equities | 2.89× | 3.00× |
| Best glide-path cohort | 1975→2021: 292 | 1975→2021: 287 |
| Worst glide-path cohort | 1945→1991: 178 | 1945→1991: 178 |
| Best/worst, glide path | 1.64× | 1.61× |
| Medians (equities / glide path) | 371 / 227 | 367 / 224 |
| R², terminal wealth vs last-10 / first-10 equity returns | 0.58 / 0.08 | 0.61 / 0.08 |
| Negative real bond years | 38 of 80 | 40 of 80 |
| Worst real bond year | 2022, −22.81% | 2022, −23.92% |
| Rolling 10-yr stock–bond correlation (positive / negative windows) | 42 / 29 | 42 / 29 |

The same cohorts come out best and worst in both runs, and every Checkpoint 4 conclusion holds in both. The inflation measure changes magnitudes by a few percent but no conclusion. The largest effect is on the worst equity cohort, because that cohort's final year is 2008, where the two inflation measures differ most.

## 4. Differences in conclusions

**Where the two summaries agree:** dispersion under pure equities is large (about 3×). Late-career returns dominate early-career returns. The glide path narrows dispersion but gives up about 39% of median wealth. Bonds are risky in real terms and were not a hedge in 2022. Birth year is a major source of luck.

**Claims in `summary_findings.txt` that the data do not support:**

1. **"The glide path … functions as insurance, reducing the worst outcomes."** Its own numbers contradict this. The worst glide-path outcome (178) is *below* the worst equity outcome (201 in its numbers, 210 in mine). The glide path narrows the best-to-worst *ratio* mostly by cutting the top. It does not raise the floor. It beat pure equities for only 1 of 35 cohorts (1963), and by only about 14% under either inflation measure. This branch says this explicitly ("cut *relative* dispersion but did not raise the floor").
2. **"Invalidating the conventional assumption that bonds provide a safe haven."** One year (2022) cannot invalidate a general assumption. The data show 12–13 years in which stocks and bonds both fell in real terms, and a stock–bond correlation that flips sign across periods. That supports "unreliable," not "invalidated."
3. **"No savings discipline or contribution level can offset a sufficiently adverse sequence."** The simulation never varies contributions. In this model terminal wealth scales in proportion to contributions, so a higher contribution level does offset a lower return in dollar terms. This claim goes beyond the exercise, and it edges toward the policy commentary Part 5 rules out.
4. **"Birth year … entirely determines."** Within this model that is true by construction, but the summary does not say that it rests on 35 heavily overlapping cohorts (neighbors share 45 of 46 return years) from a single historical path. This branch adds that caveat.

**Analysis this branch adds that the other branch lacks:**
- It explains **what drives glide-path outcomes**: career-average real bond returns (correlation +0.77). That is why the earliest cohorts, who went through the 1970s–80s bond losses mid-career, and the latest cohorts, hit by 2022 near retirement, did worst under the glide path.
- It reports the **negative correlation** between glide-path wealth and first-10-year equity returns (−0.59), and explains it as a result of the historical periods cohorts happened to share, not a modeling error.
- It shows that the eventual worst equity cohort was **ahead** of the eventual best cohort through age 64.
- It includes a chart of the rolling stock–bond correlation, and the equity/glide ratio for every cohort (median 1.71, range 0.88–2.83).

## 5. Takeaway
The two runs agree on the numbers once the inflation measure is fixed, and they agree on the direction of every finding. The other branch's quantitative work is correct. Its weaknesses are marking a failed checkpoint as passed, and three summary sentences that go beyond or against its own results: the claim that the glide path reduces the worst outcomes, "invalidating" safe-haven status, and the claim about contribution levels.
