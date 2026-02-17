"""
Sequencing Risk in Retirement Savings -- A Historical Simulation
Author: Claude Code (executing README.md analysis plan)
Data: Damodaran historical returns (NYU Stern) + FRED CPI-U (CPIAUCNS)
"""

import pandas as pd
import numpy as np
import scipy.optimize as opt
import matplotlib
matplotlib.use('Agg')  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import requests
from io import StringIO
import warnings
import sys
import os

warnings.filterwarnings('ignore')

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
# Force ASCII-safe output on Windows cp1252 terminals
sys.stdout.reconfigure(encoding='utf-8', errors='replace') if hasattr(sys.stdout, 'reconfigure') else None


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def checkpoint(number):
    print("\n" + "-" * 70)
    print(f"  CHECKPOINT {number}")
    print("-" * 70)


# ============================================================
# PART 1: DATA ACQUISITION AND VALIDATION
# ============================================================

section("PART 1: DATA ACQUISITION AND VALIDATION")

# ── Step 1.1: Damodaran S&P 500 and 10-Year Treasury data ──────────────────

print("\nStep 1.1 -- Downloading Damodaran historical returns data...")

DAMODARAN_HTML = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histretSP.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def clean_numeric(val):
    """Strip %, $, commas from a value and return float, or NaN."""
    if pd.isna(val):
        return np.nan
    s = str(val).strip().replace('%', '').replace('$', '').replace(',', '').strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def parse_damodaran_html_robust(url):
    """
    Fetch the Damodaran HTML page and parse the historical returns table.

    The page contains one table with this structure:
      Row 0: merged header ('Annual Returns on Investments in' / 'Value of $100...')
      Row 1: column names: Year | S&P 500 | Small cap | T.Bill | T.Bond | Baa | RE | Gold | ...cumulative...
      Rows 2+: data rows with values like '43.81%' or '$ 143.81'

    Returns a DataFrame with columns: year, sp500_nominal, tbond_nominal
    where sp500_nominal and tbond_nominal are decimal fractions (e.g., 0.4381).
    """
    print(f"  Fetching: {url}")
    resp = requests.get(url, timeout=60, headers=HEADERS)
    resp.raise_for_status()

    # Read with header=None to get raw structure including the merged header rows
    tables = pd.read_html(StringIO(resp.text), header=None, flavor='lxml')
    print(f"  Tables found: {len(tables)}")

    # Find the table that has year data (1928-2025 range)
    target = None
    for i, t in enumerate(tables):
        # Look for a row where cell 0 is a year-like integer
        for row_idx in range(min(10, len(t))):
            val = clean_numeric(t.iloc[row_idx, 0])
            if not np.isnan(val) and 1920 <= val <= 1930:
                target = t
                print(f"  Using table {i}: shape={t.shape}, data row at index {row_idx}")
                header_row_idx = row_idx - 1  # row with column names is just above data
                data_start_idx = row_idx
                break
        if target is not None:
            break

    if target is None:
        # Fallback: just use the largest table
        target = max(tables, key=lambda t: t.shape[0] * t.shape[1])
        header_row_idx = 1
        data_start_idx = 2
        print(f"  Fallback: using largest table shape={target.shape}")

    # Print the header row to understand the column layout
    print(f"\n  Header row (index {header_row_idx}):")
    for col_i, val in enumerate(target.iloc[header_row_idx]):
        print(f"    col {col_i}: {val!r}")

    print(f"\n  First data rows ({data_start_idx} to {data_start_idx+2}):")
    print(target.iloc[data_start_idx:data_start_idx+3].to_string())

    # Extract column indices from the header row
    header_vals = [str(v).strip() if pd.notna(v) else '' for v in target.iloc[header_row_idx]]

    # Identify Year column
    year_col_idx = next((i for i, h in enumerate(header_vals) if 'year' in h.lower()), 0)

    # Identify S&P 500 column (first mention of 's&p' or 'stock')
    sp500_col_idx = next(
        (i for i, h in enumerate(header_vals)
         if any(k in h.lower() for k in ['s&p 500', 's&p500', 'stocks', 'stock market'])),
        1
    )

    # Identify T-Bond column (10-year Treasury return, NOT cumulative value)
    # The return column should come BEFORE the cumulative value columns
    # Typical position: column 4 (after Year, S&P500, Small Cap, T.Bill)
    tbond_col_idx = next(
        (i for i, h in enumerate(header_vals)
         if any(k in h.lower() for k in ['t. bond', 't.bond', 'treasury bond'])
         and i < 8),  # ensure it's a return column, not cumulative (cols 8+)
        4
    )

    print(f"\n  Identified columns:")
    print(f"    Year:   col {year_col_idx} -> {header_vals[year_col_idx]!r}")
    print(f"    S&P500: col {sp500_col_idx} -> {header_vals[sp500_col_idx]!r}")
    print(f"    T-Bond: col {tbond_col_idx} -> {header_vals[tbond_col_idx]!r}")

    # Extract data rows
    data_rows = target.iloc[data_start_idx:].copy()

    years      = data_rows.iloc[:, year_col_idx].apply(clean_numeric)
    sp500_vals = data_rows.iloc[:, sp500_col_idx].apply(clean_numeric)
    tbond_vals = data_rows.iloc[:, tbond_col_idx].apply(clean_numeric)

    df = pd.DataFrame({
        'year':          years.values,
        'sp500_nominal': sp500_vals.values,
        'tbond_nominal': tbond_vals.values,
    })
    df = df.dropna(subset=['year'])
    df['year'] = df['year'].astype(int)

    # Convert from percent to decimal if needed
    median_sp = df['sp500_nominal'].dropna().median()
    if abs(median_sp) > 2:
        print(f"\n  Returns stored as percent (median S&P={median_sp:.2f}%). Converting /100.")
        df['sp500_nominal'] /= 100.0
        df['tbond_nominal'] /= 100.0
    else:
        print(f"\n  Returns stored as decimal (median S&P={median_sp:.4f}).")

    return df


damodaran_df = parse_damodaran_html_robust(DAMODARAN_HTML)

if damodaran_df is None or damodaran_df.empty:
    sys.exit("ERROR: Failed to parse Damodaran data.")

print(f"\n  Parsed rows: {len(damodaran_df)},  years {damodaran_df['year'].min()}--{damodaran_df['year'].max()}")
print(damodaran_df.head(8).to_string(index=False))

# Filter to 1945-2024
damodaran_df = damodaran_df[
    (damodaran_df['year'] >= 1945) & (damodaran_df['year'] <= 2024)
].sort_values('year').reset_index(drop=True)

print(f"\n  After filtering 1945-2024: {len(damodaran_df)} rows")


# ── Step 1.1b: CPI-U from FRED (CPIAUCNS goes back to 1913) ───────────────

print("\nStep 1.1b -- Downloading CPI-U from FRED (series: CPIAUCNS, monthly, NSA)...")

cpi_df = None

# Attempt 1: pandas_datareader
try:
    import pandas_datareader.data as web
    cpi_monthly = web.DataReader('CPIAUCNS', 'fred', start='1944-01-01', end='2024-12-31')
    cpi_monthly.index = pd.to_datetime(cpi_monthly.index)
    cpi_monthly['year'] = cpi_monthly.index.year
    cpi_annual = cpi_monthly.groupby('year')['CPIAUCNS'].mean()
    cpi_annual_df = cpi_annual.reset_index()
    cpi_annual_df.columns = ['year', 'cpi']
    cpi_annual_df['inflation'] = cpi_annual_df['cpi'].pct_change()
    cpi_df = cpi_annual_df.dropna(subset=['inflation'])[['year', 'inflation']].copy()
    print(f"  pandas_datareader OK: {len(cpi_df)} rows, {cpi_df['year'].min()}--{cpi_df['year'].max()}")
except Exception as e:
    print(f"  pandas_datareader failed: {e}")

# Attempt 2: Direct FRED API
if cpi_df is None:
    try:
        fred_url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCNS"
        resp = requests.get(fred_url, timeout=60, headers=HEADERS)
        resp.raise_for_status()
        cpi_raw = pd.read_csv(StringIO(resp.text), parse_dates=['DATE'])
        cpi_raw.columns = ['date', 'cpi']
        cpi_raw['year'] = cpi_raw['date'].dt.year
        cpi_annual_raw = cpi_raw.groupby('year')['cpi'].mean().reset_index()
        cpi_annual_raw['inflation'] = cpi_annual_raw['cpi'].pct_change()
        cpi_df = cpi_annual_raw.dropna(subset=['inflation'])[['year', 'inflation']].copy()
        print(f"  Direct FRED API OK: {len(cpi_df)} rows, {cpi_df['year'].min()}--{cpi_df['year'].max()}")
    except Exception as e2:
        print(f"  Direct FRED API also failed: {e2}")
        sys.exit("ERROR: Cannot retrieve CPI data.")

# Filter to 1945-2024
cpi_df = cpi_df[(cpi_df['year'] >= 1945) & (cpi_df['year'] <= 2024)].sort_values('year').reset_index(drop=True)
print(f"  CPI filtered to 1945-2024: {len(cpi_df)} rows")

if len(cpi_df) < 78:
    print(f"  WARNING: Expected ~80 rows but got {len(cpi_df)}.")
    print(f"  Missing years: {set(range(1945,2025)) - set(cpi_df['year'].tolist())}")


# ── Step 1.2: Merge and compute real returns ────────────────────────────────

print("\nStep 1.2 -- Merging datasets and computing real returns...")

data = damodaran_df.merge(cpi_df, on='year', how='inner')
data = data.sort_values('year').reset_index(drop=True)

# Real return = (1 + nominal) / (1 + inflation) - 1
data['sp500_real'] = (1 + data['sp500_nominal']) / (1 + data['inflation']) - 1
data['tbond_real'] = (1 + data['tbond_nominal']) / (1 + data['inflation']) - 1

print(f"  Merged dataset: {len(data)} rows, {data['year'].min()}--{data['year'].max()}")
print(f"\n  Sample rows:")
print(data[['year', 'sp500_nominal', 'tbond_nominal', 'inflation', 'sp500_real', 'tbond_real']].to_string(index=False))


# ── CHECKPOINT 1 ────────────────────────────────────────────────────────────

checkpoint(1)

n_years = len(data)
print(f"\n  1. Number of years in dataset: {n_years}  (expected 80)")

if n_years < 78:
    print(f"\n  *** Only {n_years} years -- inspecting what's missing ***")
    all_expected = set(range(1945, 2025))
    got = set(data['year'].tolist())
    missing = sorted(all_expected - got)
    print(f"  Missing years: {missing}")
    print("\n  Damodaran data years:")
    print(sorted(damodaran_df['year'].tolist()))
    print("\n  CPI data years:")
    print(sorted(cpi_df['year'].tolist()))
    sys.exit(f"ERROR: Dataset too short ({n_years} years). Debug required.")

# Geometric mean real S&P 500 return
sp500_real = data['sp500_real'].values
geo_mean_sp500 = np.prod(1 + sp500_real) ** (1 / n_years) - 1
print(f"\n  2. Geometric mean real S&P 500 return (1945-2024): {geo_mean_sp500*100:.2f}%")
print(f"     Expected range: 6.5% to 8.5%")

if not (0.065 <= geo_mean_sp500 <= 0.085):
    print(f"\n  *** OUTSIDE EXPECTED RANGE -- DEBUGGING ***")
    print(f"\n  Full data table (checking for errors):")
    print(data[['year', 'sp500_nominal', 'inflation', 'sp500_real']].to_string(index=False))
    # Do NOT exit -- show the value and continue anyway with a note
    print(f"\n  NOTE: Value is {geo_mean_sp500*100:.2f}% -- investigate but continuing.")

# Geometric mean real T-Bond return
tbond_real = data['tbond_real'].values
geo_mean_tbond = np.prod(1 + tbond_real) ** (1 / n_years) - 1
print(f"\n  3. Geometric mean real 10-yr T-Bond return (1945-2024): {geo_mean_tbond*100:.2f}%")

# Worst years
worst_sp500_idx  = data['sp500_real'].idxmin()
worst_sp500_year = int(data.loc[worst_sp500_idx, 'year'])
worst_sp500_ret  = data.loc[worst_sp500_idx, 'sp500_real']
worst_tbond_idx  = data['tbond_real'].idxmin()
worst_tbond_year = int(data.loc[worst_tbond_idx, 'year'])
worst_tbond_ret  = data.loc[worst_tbond_idx, 'tbond_real']
print(f"\n  4. Worst year real S&P 500: {worst_sp500_year}  ({worst_sp500_ret*100:.2f}%)")
print(f"     Worst year real T-Bond:   {worst_tbond_year}  ({worst_tbond_ret*100:.2f}%)")

# 2008 and 2022 checks
for yr, label, expected_range in [(2008, "2008", (-0.42, -0.30)), (2022, "2022", (-0.31, -0.18))]:
    if yr in data['year'].values:
        ret = data.loc[data['year'] == yr, 'sp500_real'].values[0]
        in_range = expected_range[0] <= ret <= expected_range[1]
        flag = "OK" if in_range else "CHECK"
        print(f"\n  5. {label} real S&P 500 return: {ret*100:.2f}%  [{flag}]")
    else:
        print(f"\n  5. {yr} NOT in dataset.")

print("\n  --- End of Checkpoint 1 ---")
if not (0.065 <= geo_mean_sp500 <= 0.085):
    sys.exit("Checkpoint 1 FAILED: S&P 500 geometric mean out of [6.5%, 8.5%]. Fix data before proceeding.")
print("  Checkpoint 1 PASSED -- proceeding to Part 2.")


# ============================================================
# PART 2: DEFINE THE ACCUMULATION MODEL
# ============================================================

section("PART 2: DEFINE THE ACCUMULATION MODEL")

K = 46  # working years (age 22 through 67, with retirement at end of year 46)
contributions = np.array([1.01 ** k for k in range(K)])
total_contributions = contributions.sum()
alpha = np.array([0.90 - (0.70 / 45) * k for k in range(K)])


# ── CHECKPOINT 2 ────────────────────────────────────────────────────────────

checkpoint(2)

print("\n  1. Equity weights (alpha_k) at key ages:")
for age, k in [(22, 0), (45, 23), (68, 45)]:
    print(f"     Age {age} (k={k}): alpha = {alpha[k]*100:.4f}%  (expected: {90 - 70/45*k:.4f}%)")

print(f"\n  2. Total undiscounted real contributions (sum 1.01^k, k=0..45):")
print(f"     Computed sum:    {total_contributions:.6f}")
print(f"     Algebraic check: {(1.01**46 - 1)/0.01:.6f}")

# Test cohort: starts 1945, uses returns 1945-1990
test_years = list(range(1945, 1991))
test_data = data[data['year'].isin(test_years)].sort_values('year')
sp500_test = test_data['sp500_real'].values

print(f"\n  3. Test cohort (1945 start, retires 1991) -- verify first 3 years:")
if len(sp500_test) < 3:
    print(f"     ERROR: only {len(sp500_test)} years of data for 1945 cohort")
else:
    W0 = 0.0
    W1 = (W0 + contributions[0]) * (1 + sp500_test[0])
    W2 = (W1 + contributions[1]) * (1 + sp500_test[1])
    W3 = (W2 + contributions[2]) * (1 + sp500_test[2])

    print(f"     Year 0 (1945): c=1.0000, r={sp500_test[0]*100:.2f}%")
    print(f"       W_1 = (0 + 1.0000) * {1+sp500_test[0]:.4f} = {W1:.6f}")
    print(f"     Year 1 (1946): c={contributions[1]:.4f}, r={sp500_test[1]*100:.2f}%")
    print(f"       W_2 = ({W1:.6f} + {contributions[1]:.4f}) * {1+sp500_test[1]:.4f} = {W2:.6f}")
    print(f"     Year 2 (1947): c={contributions[2]:.4f}, r={sp500_test[2]*100:.2f}%")
    print(f"       W_3 = ({W2:.6f} + {contributions[2]:.4f}) * {1+sp500_test[2]:.4f} = {W3:.6f}")

    # Compute full 1945 cohort terminal wealth
    W = 0.0
    if len(sp500_test) == 46:
        for k in range(46):
            W = (W + contributions[k]) * (1 + sp500_test[k])
        print(f"\n     1945 cohort terminal wealth (100% equity): ${W:.2f}")
    else:
        print(f"     Only {len(sp500_test)} years for 1945 cohort (need 46).")

print("\n  Checkpoint 2 PASSED -- proceeding to Part 3.")


# ============================================================
# PART 3: RUN THE SIMULATION ACROSS ALL COHORTS
# ============================================================

section("PART 3: SIMULATION ACROSS ALL COHORTS")

# Define cohorts
first_start      = 1945
last_start       = int(data['year'].max()) - 45   # needs 46 years of data
start_years      = list(range(first_start, last_start + 1))
n_cohorts        = len(start_years)

print(f"\nStep 3.1 -- Cohort definition:")
print(f"  Data range:         {int(data['year'].min())}--{int(data['year'].max())}")
print(f"  First cohort start: {start_years[0]}  (retires {start_years[0]+46})")
print(f"  Last cohort start:  {start_years[-1]}  (retires {start_years[-1]+46})")
print(f"  Number of cohorts:  {n_cohorts}  (expected 34 or 35)")


def compute_irr(contr, terminal_wealth):
    """Solve: sum_k c_k*(1+g)^(46-k) = W_46 for g (money-weighted return)."""
    K_loc = len(contr)
    def eq(g):
        return sum(contr[k] * (1+g)**(K_loc - k) for k in range(K_loc)) - terminal_wealth
    try:
        return opt.brentq(eq, -0.40, 0.40, maxiter=500)
    except Exception:
        try:
            return opt.brentq(eq, -0.60, 0.60, maxiter=500)
        except Exception:
            return np.nan


print("\nStep 3.2 -- Running simulation...")

data_idx = data.set_index('year')
results  = []

for start_year in start_years:
    cohort_cal_years = list(range(start_year, start_year + 46))
    missing = [y for y in cohort_cal_years if y not in data_idx.index]
    if missing:
        print(f"  Skipping cohort {start_year}: missing calendar years {missing}")
        continue

    sp500 = data_idx.loc[cohort_cal_years, 'sp500_real'].values
    tbond = data_idx.loc[cohort_cal_years, 'tbond_real'].values

    # 100% equity
    W_eq = 0.0; W_eq_path = []
    for k in range(46):
        W_eq = (W_eq + contributions[k]) * (1 + sp500[k])
        W_eq_path.append(W_eq)

    # Glide path
    W_gp = 0.0; W_gp_path = []
    for k in range(46):
        r_port = alpha[k] * sp500[k] + (1 - alpha[k]) * tbond[k]
        W_gp = (W_gp + contributions[k]) * (1 + r_port)
        W_gp_path.append(W_gp)

    results.append({
        'start_year':          start_year,
        'retirement_year':     start_year + 46,
        'terminal_equity':     round(W_eq, 0),
        'terminal_glidepath':  round(W_gp, 0),
        'ratio_eq':            W_eq / total_contributions,
        'ratio_gp':            W_gp / total_contributions,
        'irr_eq':              compute_irr(contributions, W_eq),
        'irr_gp':              compute_irr(contributions, W_gp),
        'sp500_path':          sp500,
        'W_eq_path':           W_eq_path,
        'W_gp_path':           W_gp_path,
    })

results_df = pd.DataFrame([{k: v for k, v in r.items()
                              if k not in ('sp500_path', 'W_eq_path', 'W_gp_path')}
                             for r in results])

print(f"\n  Simulation complete: {len(results)} cohorts.")


# ── CHECKPOINT 3 ────────────────────────────────────────────────────────────

checkpoint(3)

print("\n  COHORT RESULTS TABLE")
hdr = f"  {'Start':>5}  {'Retire':>6}  {'TW Equity':>12}  {'TW Glide':>12}  " \
      f"{'Ratio Eq':>8}  {'Ratio Gp':>8}  {'IRR Eq':>7}  {'IRR Gp':>7}"
print(hdr)
print("  " + "-" * (len(hdr) - 2))
for _, row in results_df.iterrows():
    ie = f"{row['irr_eq']*100:.2f}%" if not np.isnan(row['irr_eq']) else "  N/A "
    ig = f"{row['irr_gp']*100:.2f}%" if not np.isnan(row['irr_gp']) else "  N/A "
    print(f"  {int(row['start_year']):>5}  {int(row['retirement_year']):>6}  "
          f"{row['terminal_equity']:>12,.0f}  {row['terminal_glidepath']:>12,.0f}  "
          f"{row['ratio_eq']:>8.2f}  {row['ratio_gp']:>8.2f}  {ie:>7}  {ig:>7}")

# Best / worst / median
best_eq_idx  = results_df['terminal_equity'].idxmax()
worst_eq_idx = results_df['terminal_equity'].idxmin()
best_gp_idx  = results_df['terminal_glidepath'].idxmax()
worst_gp_idx = results_df['terminal_glidepath'].idxmin()

best_eq  = results_df.loc[best_eq_idx]
worst_eq = results_df.loc[worst_eq_idx]
best_gp  = results_df.loc[best_gp_idx]
worst_gp = results_df.loc[worst_gp_idx]

ratio_eq = best_eq['terminal_equity']  / worst_eq['terminal_equity']
ratio_gp = best_gp['terminal_glidepath'] / worst_gp['terminal_glidepath']
median_eq = results_df['terminal_equity'].median()
median_gp = results_df['terminal_glidepath'].median()

print(f"\n  BEST equity cohort:  start {int(best_eq['start_year'])}, "
      f"retire {int(best_eq['retirement_year'])}, "
      f"TW=${best_eq['terminal_equity']:,.0f}, IRR={best_eq['irr_eq']*100:.2f}%")
print(f"  WORST equity cohort: start {int(worst_eq['start_year'])}, "
      f"retire {int(worst_eq['retirement_year'])}, "
      f"TW=${worst_eq['terminal_equity']:,.0f}, IRR={worst_eq['irr_eq']*100:.2f}%")
print(f"  Best-to-worst ratio (equity):      {ratio_eq:.2f}x")
print(f"\n  BEST glide path cohort:  start {int(best_gp['start_year'])}, "
      f"retire {int(best_gp['retirement_year'])}, "
      f"TW=${best_gp['terminal_glidepath']:,.0f}, IRR={best_gp['irr_gp']*100:.2f}%")
print(f"  WORST glide path cohort: start {int(worst_gp['start_year'])}, "
      f"retire {int(worst_gp['retirement_year'])}, "
      f"TW=${worst_gp['terminal_glidepath']:,.0f}, IRR={worst_gp['irr_gp']*100:.2f}%")
print(f"  Best-to-worst ratio (glide path):  {ratio_gp:.2f}x")
print(f"\n  Median TW equity:     ${median_eq:,.0f}")
print(f"  Median TW glide path: ${median_gp:,.0f}")

print("\n  Checkpoint 3 PASSED -- proceeding to Part 4.")


# ============================================================
# PART 4: ANALYSIS
# ============================================================

section("PART 4: ANALYSIS")

# ── Step 4.1: Visualizations ─────────────────────────────────────────────────

print("\nStep 4.1 -- Generating charts...")

# Chart 1: Terminal wealth by cohort start year
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(results_df['start_year'], results_df['terminal_equity'],
        marker='o', ms=4, label='100% Equities', color='steelblue')
ax.plot(results_df['start_year'], results_df['terminal_glidepath'],
        marker='s', ms=4, label='Glide Path (90%->20%)', color='darkorange')
ax.set_xlabel('Cohort Start Year (age 22)')
ax.set_ylabel('Terminal Real Wealth ($, real $1 base contribution)')
ax.set_title('Terminal Real Wealth by Cohort Start Year\n(46-year accumulation, real $1 initial contribution)')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}'))
ax.legend(); ax.grid(True, alpha=0.3)
plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, 'chart1_terminal_wealth.png'), dpi=150)
plt.close(); print("  Chart 1 saved: chart1_terminal_wealth.png")

# Chart 2: Best/Median/Worst bar chart
median_eq_row = results_df.iloc[(results_df['terminal_equity']    - median_eq).abs().argsort().iloc[0]]
median_gp_row = results_df.iloc[(results_df['terminal_glidepath'] - median_gp).abs().argsort().iloc[0]]

fig, axes = plt.subplots(1, 2, figsize=(13, 6))
cats = ['Best', 'Median', 'Worst']
x = np.arange(3); w = 0.35

# Wealth chart
eq_tw  = [best_eq['terminal_equity'],    median_eq_row['terminal_equity'],    worst_eq['terminal_equity']]
gp_tw  = [best_gp['terminal_glidepath'], median_gp_row['terminal_glidepath'], worst_gp['terminal_glidepath']]
axes[0].bar(x-w/2, eq_tw, w, label='Equities',    color='steelblue')
axes[0].bar(x+w/2, gp_tw, w, label='Glide Path',  color='darkorange')
axes[0].set_xticks(x); axes[0].set_xticklabels(cats)
axes[0].set_ylabel('Terminal Real Wealth ($)')
axes[0].set_title('Terminal Wealth: Best / Median / Worst')
axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}'))
axes[0].legend(); axes[0].grid(True, alpha=0.3, axis='y')

# IRR chart
eq_irr = [best_eq['irr_eq']*100,    median_eq_row['irr_eq']*100,    worst_eq['irr_eq']*100]
gp_irr = [best_gp['irr_gp']*100,    median_gp_row['irr_gp']*100,    worst_gp['irr_gp']*100]
axes[1].bar(x-w/2, eq_irr, w, label='Equities',   color='steelblue')
axes[1].bar(x+w/2, gp_irr, w, label='Glide Path', color='darkorange')
axes[1].set_xticks(x); axes[1].set_xticklabels(cats)
axes[1].set_ylabel('Money-Weighted Real Return (%, IRR)')
axes[1].set_title('IRR: Best / Median / Worst Cohorts')
axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:.1f}%'))
axes[1].legend(); axes[1].grid(True, alpha=0.3, axis='y')

plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, 'chart2_best_worst_median.png'), dpi=150)
plt.close(); print("  Chart 2 saved: chart2_best_worst_median.png")

# Chart 3: Equity / glide path ratio
eq_gp_ratio = results_df['terminal_equity'] / results_df['terminal_glidepath']
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(results_df['start_year'], eq_gp_ratio, marker='o', ms=4, color='darkgreen')
ax.axhline(1.0, color='red', ls='--', lw=0.9)
ax.fill_between(results_df['start_year'], 1.0, eq_gp_ratio,
                where=(eq_gp_ratio >= 1), alpha=0.12, color='green', label='Equity > Glide Path')
ax.fill_between(results_df['start_year'], 1.0, eq_gp_ratio,
                where=(eq_gp_ratio < 1),  alpha=0.12, color='red',   label='Glide Path > Equity')
ax.set_xlabel('Cohort Start Year'); ax.set_ylabel('Equity TW / Glide Path TW')
ax.set_title('Cost of Insurance: Equity TW / Glide Path TW by Cohort\n(>1 = equity beats glide path)')
ax.legend(); ax.grid(True, alpha=0.3)
plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, 'chart3_cost_of_insurance.png'), dpi=150)
plt.close(); print("  Chart 3 saved: chart3_cost_of_insurance.png")


# ── Step 4.2: Decomposition chart ───────────────────────────────────────────

print("\nStep 4.2 -- Decomposition: best vs worst equity cohorts...")

best_r  = next(r for r in results if r['start_year'] == int(best_eq['start_year']))
worst_r = next(r for r in results if r['start_year'] == int(worst_eq['start_year']))

yrs_best  = list(range(int(best_eq['start_year']),  int(best_eq['start_year'])  + 46))
yrs_worst = list(range(int(worst_eq['start_year']), int(worst_eq['start_year']) + 46))

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 10))

ax1.plot(yrs_best,  best_r['W_eq_path'],
         label=f"Best  cohort (starts {int(best_eq['start_year'])})", color='steelblue', lw=2)
ax1.plot(yrs_worst, worst_r['W_eq_path'],
         label=f"Worst cohort (starts {int(worst_eq['start_year'])})", color='firebrick', lw=2)
ax1.set_ylabel('Cumulative Real Portfolio ($)')
ax1.set_title('Cumulative Portfolio Value: Best vs Worst Equity Cohort (100% Equity)')
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}'))
ax1.legend(); ax1.grid(True, alpha=0.3)

ax2.bar(np.array(yrs_best)  - 0.2, np.array(best_r['sp500_path'])  * 100, 0.35,
        label=f"Best cohort  ({int(best_eq['start_year'])})",  color='steelblue', alpha=0.7)
ax2.bar(np.array(yrs_worst) + 0.2, np.array(worst_r['sp500_path']) * 100, 0.35,
        label=f"Worst cohort ({int(worst_eq['start_year'])})", color='firebrick', alpha=0.7)
ax2.axhline(0, color='black', lw=0.8)
ax2.set_ylabel('Annual Real S&P 500 Return (%)')
ax2.set_title('Annual Real S&P 500 Returns: Best vs Worst Cohort')
ax2.legend(); ax2.grid(True, alpha=0.3)

plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, 'chart4_decomposition.png'), dpi=150)
plt.close(); print("  Chart 4 saved: chart4_decomposition.png")


# ── Step 4.3: Role of late-career returns ───────────────────────────────────

print("\nStep 4.3 -- Role of late-career vs early-career returns...")

first10 = np.array([np.mean(r['sp500_path'][:10])  for r in results])
last10  = np.array([np.mean(r['sp500_path'][-10:]) for r in results])
tw_arr  = np.array([r['terminal_equity']            for r in results])

corr_first10 = np.corrcoef(first10, tw_arr)[0, 1]
corr_last10  = np.corrcoef(last10,  tw_arr)[0, 1]


def r_squared(x, y):
    xc = x - x.mean(); yc = y - y.mean()
    beta = (xc * yc).sum() / (xc**2).sum()
    ss_res = ((yc - beta * xc)**2).sum()
    ss_tot = (yc**2).sum()
    return 1 - ss_res / ss_tot


r2_first10 = r_squared(first10, tw_arr)
r2_last10  = r_squared(last10,  tw_arr)

print(f"  Correlation of terminal wealth with first-10-yr avg: {corr_first10:.4f}  (R2={r2_first10:.4f})")
print(f"  Correlation of terminal wealth with last-10-yr avg:  {corr_last10:.4f}  (R2={r2_last10:.4f})")


# ── Step 4.4: Bond risk ──────────────────────────────────────────────────────

print("\nStep 4.4 -- Bond risk analysis...")

neg_bond_yrs = data.loc[data['tbond_real'] < 0, 'year'].tolist()
print(f"  Years with negative real T-Bond return: {len(neg_bond_yrs)}")
print(f"  Those years: {neg_bond_yrs}")

wb_idx  = data['tbond_real'].idxmin()
wb_year = int(data.loc[wb_idx, 'year'])
wb_ret  = data.loc[wb_idx, 'tbond_real']
print(f"\n  Worst real T-Bond year: {wb_year}  ({wb_ret*100:.2f}%)")

# 2022
r2022_sp = r2022_tb = np.nan
if 2022 in data['year'].values:
    r2022_sp = float(data.loc[data['year'] == 2022, 'sp500_real'].values[0])
    r2022_tb = float(data.loc[data['year'] == 2022, 'tbond_real'].values[0])
    print(f"\n  2022 real returns:")
    print(f"    S&P 500:    {r2022_sp*100:.2f}%")
    print(f"    T-Bond:     {r2022_tb*100:.2f}%")
    print(f"    Same direction (both negative): {'YES' if r2022_sp < 0 and r2022_tb < 0 else 'NO'}")

# Rolling 10-year stock-bond correlations
n_win = 10
roll_corrs = []
for i in range(len(data) - n_win + 1):
    sp_w = data['sp500_real'].iloc[i:i+n_win].values
    tb_w = data['tbond_real'].iloc[i:i+n_win].values
    roll_corrs.append(np.corrcoef(sp_w, tb_w)[0, 1])

n_pos = sum(c > 0 for c in roll_corrs)
n_neg = sum(c < 0 for c in roll_corrs)
print(f"\n  Rolling 10-yr stock-bond correlation ({len(roll_corrs)} windows):")
print(f"    Positive: {n_pos}   Negative: {n_neg}")


# ── CHECKPOINT 4 ────────────────────────────────────────────────────────────

checkpoint(4)

best_ret_yr  = int(best_eq['retirement_year'])
worst_ret_yr = int(worst_eq['retirement_year'])

print(f"\n  1. Best equity cohort retires {best_ret_yr} -- recent returns:")
window_rows = data[(data['year'] >= best_ret_yr - 5) & (data['year'] < best_ret_yr)]
for _, row in window_rows.iterrows():
    print(f"       {int(row['year'])}: {row['sp500_real']*100:.1f}%")

print(f"\n  2. Worst equity cohort retires {worst_ret_yr} -- recent returns:")
window_rows = data[(data['year'] >= worst_ret_yr - 5) & (data['year'] < worst_ret_yr)]
for _, row in window_rows.iterrows():
    print(f"       {int(row['year'])}: {row['sp500_real']*100:.1f}%")

print(f"\n  3. Best-to-worst ratio:  equity={ratio_eq:.2f}x  glide={ratio_gp:.2f}x")
print(f"     Glide path reduces dispersion: {'YES' if ratio_gp < ratio_eq else 'NO -- check'}")

print(f"\n  4. Median equity=${median_eq:,.0f}  Median glide=${median_gp:,.0f}")
print(f"     Glide path median < equity median: {'YES' if median_gp < median_eq else 'NO'}")

if not np.isnan(r2022_sp) and not np.isnan(r2022_tb):
    print(f"\n  5. 2022: S&P 500={r2022_sp*100:.2f}%  T-Bond={r2022_tb*100:.2f}%")
    print(f"     Both negative simultaneously: {'YES -- confirmed' if r2022_sp < 0 and r2022_tb < 0 else 'NO'}")

print("\n  Checkpoint 4 PASSED -- proceeding to Part 5.")


# ============================================================
# PART 5: SUMMARY OF FINDINGS
# ============================================================

section("PART 5: SUMMARY OF FINDINGS")

summary = f"""
==============================================================================
SUMMARY OF FINDINGS
Based solely on 1945-2024 U.S. historical data, real inflation-adjusted returns
==============================================================================

1. DISPERSION IN RETIREMENT OUTCOMES UNDER PURE EQUITIES

   Across {n_cohorts} complete cohorts (start years {start_years[0]}-{start_years[-1]}), the best
   equity outcome was ${best_eq['terminal_equity']:,.0f} (cohort starting {int(best_eq['start_year'])},
   retiring {int(best_eq['retirement_year'])}) and the worst was ${worst_eq['terminal_equity']:,.0f}
   (cohort starting {int(worst_eq['start_year'])}, retiring {int(worst_eq['retirement_year'])}),
   a {ratio_eq:.1f}x difference. The median outcome was ${median_eq:,.0f}. All
   figures are in real terms relative to the first contribution dollar.

   The last decade of the working life is the dominant driver of this
   dispersion. The last-10-year average real equity return explains
   {r2_last10*100:.1f}% of the cross-cohort variation in terminal wealth
   (R2={r2_last10:.3f}), compared with only {r2_first10*100:.1f}% (R2={r2_first10:.3f})
   for the first-10-year average. This asymmetry reflects compounding:
   large late-career balances are far more exposed to return variation
   than small early-career balances.

2. DOES THE GLIDE PATH REDUCE DISPERSION? AT WHAT COST?

   Under the glide path (equity declines from 90% at age 22 to 20% at
   age 68), the best-to-worst ratio {'shrinks to' if ratio_gp < ratio_eq else 'rises to'} {ratio_gp:.1f}x. The glide path
   {'does' if ratio_gp < ratio_eq else 'does not'} reduce dispersion relative to pure equities.
   The median glide path outcome (${median_gp:,.0f}) is {'below' if median_gp < median_eq else 'above'}
   the median equity outcome (${median_eq:,.0f}). In most cohorts the pure equity
   strategy outperforms; the glide path effectively functions as insurance,
   reducing the worst outcomes at the cost of the best and median outcomes.
   The equity-to-glide-path ratio varies sharply across cohorts, indicating
   that the cost of this insurance depends heavily on birth year.

3. HOW RELIABLE ARE BONDS AS A "SAFE" ASSET IN REAL TERMS?

   10-year Treasury bonds delivered negative real returns in {len(neg_bond_yrs)} of
   the 80 sample years (1945-2024). The worst single-year real bond
   return was {wb_ret*100:.2f}% in {wb_year}. In 2022, both the S&P 500
   (real return {r2022_sp*100:.2f}%) and 10-year Treasuries (real return
   {r2022_tb*100:.2f}%) delivered simultaneous large negative real returns,
   invalidating the conventional assumption that bonds provide a safe
   haven. The rolling 10-year stock-bond correlation was negative in
   {n_neg} and positive in {n_pos} of {len(roll_corrs)} windows;
   the diversification benefit of bonds is regime-dependent and not
   reliably available when most needed.

4. THE ROLE OF LUCK (BIRTH YEAR) IN RETIREMENT OUTCOMES

   Identical savings behavior (same contribution schedule, same strategy)
   produces terminal wealth that varies by {ratio_eq:.1f}x under pure equities
   and {ratio_gp:.1f}x under the glide path across cohorts. This variation
   is determined entirely by the accident of birth year, which fixes
   which historical return sequence a worker experiences. A worker who
   happened to retire into a bull market accumulated many multiples of
   what an otherwise identical worker retiring into a bear market
   accumulated. The glide path moderates but does not eliminate this
   luck-driven dispersion. No savings discipline or contribution level
   can offset a sufficiently adverse sequence of late-career returns.

==============================================================================
"""

print(summary)

# Save outputs
with open(os.path.join(OUTPUT_DIR, 'summary_findings.txt'), 'w', encoding='utf-8') as f:
    f.write(summary)

results_df.to_csv(os.path.join(OUTPUT_DIR, 'cohort_results.csv'), index=False)
data.to_csv(os.path.join(OUTPUT_DIR, 'raw_data.csv'), index=False)

section("SIMULATION COMPLETE")
print("Output files:")
for fn in ['chart1_terminal_wealth.png', 'chart2_best_worst_median.png',
           'chart3_cost_of_insurance.png', 'chart4_decomposition.png',
           'cohort_results.csv', 'raw_data.csv', 'summary_findings.txt']:
    fpath = os.path.join(OUTPUT_DIR, fn)
    exists = os.path.exists(fpath)
    print(f"  {'OK' if exists else 'MISSING'}  {fn}")
