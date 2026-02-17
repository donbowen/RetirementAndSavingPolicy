# Prompt: Sequencing Risk in Retirement Savings — A Historical Simulation

You are a financial economist. Your task is to build a rigorous simulation of how the *ordering* of investment returns over a working lifetime affects terminal retirement wealth, using actual U.S. historical data. Work through the following steps in order. At each checkpoint, report the requested diagnostics before proceeding. Do not skip checkpoints.

---

## Part 1: Data Acquisition and Validation

### Step 1.1 — Download the Data

Go to Aswath Damodaran's historical returns dataset at NYU Stern:

- URL: `https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histretSP.html`

From this dataset, extract an annual series covering **1945–2024** (80 years):

1. **S&P 500 total return (including reinvested dividends)** — nominal
2. **10-year U.S. Treasury bond total return** — nominal

Using FRED, with pandas-datareader, obtain annual **CPI-U inflation rates** as well.

### Step 1.2 — Compute Real Returns

For each year $t$, compute the real total return for both equities and bonds:

$$r_{t}^{\text{real}} = \frac{1 + r_{t}^{\text{nominal}}}{1 + \pi_t} - 1$$

where $\pi_t$ is the CPI-U inflation rate for year $t$.

### Checkpoint 1

Report the following before proceeding:

- Number of years in each series (should be 80).
- Geometric mean of the real S&P 500 total return over 1945–2024. (*Expected: approximately 7.5% per year. If your value is outside the range 6.5%–8.5%, stop and debug.*)
- Geometric mean of the real 10-year Treasury bond total return over the same period.
- Identify the single worst year for real S&P 500 returns and the single worst year for real bond returns. Report the year and the return for each.
- Confirm that 2008 real S&P 500 return is approximately −36% and that 2022 real S&P 500 return is approximately −24.5%.

---

## Part 2: Define the Accumulation Model

### Step 2.1 — Worker Profile

A worker begins investing at age 22 and retires at age 68, yielding a **46-year accumulation phase**. In their first year of work, they contribute **$1** (in real terms). Each subsequent year, their contribution grows by **1% in real terms** (approximating real wage growth). Formally, the contribution in working year $k$ (where $k = 0$ is the first year) is:

$$c_k = 1 \times 1.01^k$$

### Step 2.2 — Pure Equity Strategy

Under 100% equities, the worker invests every dollar in the S&P 500. The portfolio evolves as:

$$W_{k+1} = (W_k + c_k) \times (1 + r_{t(k)}^{\text{equity, real}})$$

where $W_0 = 0$, $c_k$ is the contribution at the *start* of year $k$, and $t(k)$ maps working year $k$ to the corresponding calendar year for a given cohort.

**Important timing convention:** The contribution is made at the start of the year and earns that year's return. Be explicit about this assumption and consistent throughout.

### Step 2.3 — Glide Path Strategy

The glide path linearly reduces equity exposure from **90% at age 22** to **20% at age 68**. In working year $k$ (where $k = 0, 1, \ldots, 45$):

$$\alpha_k = 0.90 - \frac{0.70}{45} \times k$$

where $\alpha_k$ is the equity weight. The bond weight is $1 - \alpha_k$. The portfolio return in year $k$ is:

$$r_k^{\text{portfolio}} = \alpha_k \times r_{t(k)}^{\text{equity, real}} + (1 - \alpha_k) \times r_{t(k)}^{\text{bond, real}}$$

The portfolio evolves as:

$$W_{k+1} = (W_k + c_k) \times (1 + r_k^{\text{portfolio}})$$

Rebalancing occurs annually to the target weights.

### Checkpoint 2

Before running the full simulation:

- Report the equity weight $\alpha_k$ at ages 22, 45, and 68. (*Expected: 90%, 54.2%, 20%.*)
- Report the total undiscounted real contributions over 46 years. (*This is $\sum_{k=0}^{45} 1.01^k$.*)
- For a single test cohort (the one starting in 1945, retiring in 1991), compute terminal wealth under 100% equities and verify the calculation by hand for the first 3 years.

---

## Part 3: Run the Simulation Across All Cohorts

### Step 3.1 — Define Cohorts

A cohort is defined by its start year. The first possible cohort starts in **1945** and retires in **1991** (46 years later, using returns from 1945 through 1990). The last possible cohort starts in **1979** and retires in **2025** — but since our data end in 2024, the last *complete* cohort starts in **1979** and uses returns through 2024 (46 years: 1979–2024).

**Wait — verify this.** Count carefully: a cohort starting in year $Y$ uses returns from year $Y$ through year $Y + 45$. The last year of data is 2024. So the last start year is $2024 - 45 = 1979$. The first start year is 1945. This gives $1979 - 1945 + 1 = 35$ cohorts.

**Recount if you get 34 cohorts.** Report the exact number and the start/end year of the first and last cohort. If you get a different number than 34 or 35, show your reasoning.

### Step 3.2 — Compute Terminal Wealth

For each cohort, compute:

1. Terminal real wealth under **100% equities**
2. Terminal real wealth under the **glide path**
3. The **geometric mean real annual return** for each strategy, defined as:

$$g = \left(\frac{W_{46}}{\sum_{k=0}^{45} c_k \times \prod_{j=k}^{45}(1 + r_j)^{-1}} \right)^{1/46} - 1$$

Actually, computing a single geometric mean return for a strategy with annual contributions is not straightforward — the standard geometric mean applies to a lump sum. Instead, compute the **money-weighted (IRR) real return** for each cohort-strategy pair. This is the rate $g$ that satisfies:

$$\sum_{k=0}^{45} c_k \times (1+g)^{46-k} = W_{46}$$

Use a numerical solver (e.g., `numpy.irr`, `scipy.optimize.brentq`, or Stata's IRR equivalent). If this is computationally complex, you may alternatively report the **simple ratio** $W_{46} / \sum c_k$ (terminal wealth divided by total contributions) as a summary measure of accumulation efficiency.

### Checkpoint 3

Report a table with the following columns for **every cohort**: start year, end year (retirement year), terminal wealth (equities), terminal wealth (glide path), and the IRR or wealth-to-contribution ratio for each.

Then report:

- The **best** and **worst** cohort under 100% equities (by terminal wealth). Report start year, retirement year, terminal wealth, and IRR.
- The **best** and **worst** cohort under the glide path. Same fields.
- The **ratio** of best-to-worst terminal wealth under equities.
- The **ratio** of best-to-worst terminal wealth under the glide path.
- The **median** terminal wealth under each strategy.

---

## Part 4: Analysis

### Step 4.1 — Visualizations

Produce the following charts:

1. **Line chart:** Terminal real wealth by cohort start year, with two series (equities and glide path) on the same axes.
2. **Bar chart or table:** For the best, worst, and median cohort under each strategy, show the terminal wealth and IRR side by side.
3. **Line chart:** The ratio of equity terminal wealth to glide path terminal wealth, by cohort start year. This shows the "cost of insurance" cohort by cohort.

### Step 4.2 — Decomposition

For the **best equity cohort** and the **worst equity cohort**, produce a chart showing:

- Cumulative portfolio value over the 46-year horizon (year by year)
- Annual real S&P 500 returns experienced by that cohort

Overlay the two cohorts on the same chart to make the contrast visible.

### Step 4.3 — The Role of Late-Career Returns

To quantify how much late-career returns matter relative to early-career returns, run the following auxiliary exercise:

For each cohort, compute the **correlation** between terminal wealth and the average real equity return in:
- The **first 10 years** of the cohort's working life
- The **last 10 years** of the cohort's working life

Report both correlations. Also compute: for each cohort, what fraction of terminal wealth variation across cohorts is explained by the last-10-year average return vs. the first-10-year average return? (Use $R^2$ from simple regressions.)

### Step 4.4 — Bond Risk

Report the following facts from the data:

- How many years in the 1945–2024 sample did 10-year Treasury bonds deliver a **negative real return**?
- What was the worst single-year real bond return, and in what year?
- In **2022**, what were the real returns on (a) the S&P 500 and (b) 10-year Treasuries? Did they move in the same direction?
- Compute the **rolling 10-year correlation** between annual real stock returns and annual real bond returns. In how many 10-year windows is this correlation positive vs. negative?

### Checkpoint 4

Before writing any summary or interpretation:

- Verify that the best equity cohort's retirement year coincides with a period of strong equity performance.
- Verify that the worst equity cohort's retirement year coincides with a major market downturn.
- Verify that the glide path reduces the best-to-worst ratio relative to pure equities.
- Verify that the median glide path outcome is lower than the median equity outcome.
- Confirm that 2022 shows simultaneous negative real returns for both stocks and bonds.

---

## Part 5: Summary of Findings

Based solely on the data and computations above, write a concise summary (no more than 500 words) addressing:

1. How large is the dispersion in retirement outcomes across cohorts under pure equities?
2. Does the glide path reduce this dispersion? At what cost?
3. How reliable are bonds as a "safe" asset in real terms?
4. What does this exercise imply about the role of luck (birth year) in retirement outcomes?

Do **not** make policy recommendations. Simply report what the data show.

---

## Implementation Notes

- Use Python (with `pandas`, `numpy`, `scipy`, `matplotlib`) or Stata. Show all code.
- Use real (inflation-adjusted) returns throughout. Never mix nominal and real quantities.
- Be explicit about timing conventions (start-of-year vs. end-of-year contributions).
- All dollar figures are in **real terms**, indexed to the purchasing power of the first contribution year of each cohort.
- Round terminal wealth to the nearest dollar. Round returns to two decimal places (in percentage terms).
- If any intermediate result seems implausible, stop and debug before proceeding.