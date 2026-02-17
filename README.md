# Prompt: Sequencing Risk Analysis

Using historical S&P 500 annual total returns (including dividends) and 10-year Treasury bond returns from 1945 to 2024, sourced from Aswath Damodaran's dataset at NYU Stern, I want to analyze how the timing of returns affects retirement outcomes for different cohorts of workers.

Deflate all nominal returns by CPI inflation to get real returns.

Assume a worker starts investing at age 22 and retires at age 68 (46 years). In their first year they contribute $1, and each year after that the contribution grows by 1% in real terms. Everything goes into the S&P 500.

Run this for every possible 46-year window in the data. Compare terminal wealth across cohorts.

Then do the same thing but with a glide path strategy: start at 90% stocks / 10% bonds at age 22 and linearly shift to 20% stocks / 80% bonds by age 68. Use 10-year Treasury real returns for the bond portion.

Show me:
- Terminal wealth for each cohort under both strategies
- The best and worst cohorts under each strategy
- Charts comparing the two strategies
- Some analysis of how bonds performed as a "safe" asset, especially during periods like the 1970s and 2022

Write the code in Python and show all results.

## Implementation

This repository includes `run_analysis.py`, a dependency-free Python script that performs the full analysis when the Damodaran CSV is available locally at `data/histretSP.csv`.

Run:

```bash
python run_analysis.py
```

Generated outputs:

- `outputs/cohort_terminal_wealth.csv`
- `outputs/terminal_wealth_comparison.svg`
- `outputs/report.md`

If the data file is missing, the script exits with an explicit error telling you where to place it.
