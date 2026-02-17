#!/usr/bin/env python3
"""Sequencing risk analysis for retirement cohorts using Damodaran data.

Expected input file: data/histretSP.csv
The script is dependency-free (stdlib only).
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from statistics import mean, median
from typing import Dict, List

INPUT_PATH = "data/histretSP.csv"
RESULTS_CSV = "outputs/cohort_terminal_wealth.csv"
REPORT_MD = "outputs/report.md"
SVG_PATH = "outputs/terminal_wealth_comparison.svg"

START_YEAR = 1945
END_YEAR = 2024
HORIZON = 46


@dataclass
class YearRecord:
    year: int
    stock_nominal: float
    bond_nominal: float
    inflation: float
    stock_real: float
    bond_real: float


@dataclass
class CohortResult:
    start_year: int
    end_year: int
    terminal_stock_100: float
    terminal_glide: float
    glide_minus_stock: float


def parse_percent(value: str) -> float:
    s = value.strip().replace("%", "")
    if not s:
        raise ValueError("Empty percentage value")
    return float(s) / 100.0


def normalize_header(h: str) -> str:
    return "".join(ch.lower() for ch in h if ch.isalnum())


def detect_columns(fieldnames: List[str]) -> Dict[str, str]:
    normalized = {name: normalize_header(name) for name in fieldnames}

    year = None
    for original, norm in normalized.items():
        if norm == "year":
            year = original
            break

    def find_one(candidates: List[str]) -> str | None:
        for original, norm in normalized.items():
            for cand in candidates:
                if cand in norm:
                    return original
        return None

    stock = find_one(["sp500", "sandt p500", "stocks", "stock", "spreturn"])
    bond = find_one(["tbond", "treasury", "10year", "tbon", "bond"])
    infl = find_one(["inflation", "cpi"])

    missing = [
        name
        for name, col in [("year", year), ("stock", stock), ("bond", bond), ("inflation", infl)]
        if col is None
    ]
    if missing:
        raise ValueError(
            f"Could not detect columns for: {', '.join(missing)}. "
            f"Found headers: {fieldnames}"
        )

    return {"year": year, "stock": stock, "bond": bond, "inflation": infl}


def load_records(path: str) -> List[YearRecord]:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Input file not found at {path}. Place Damodaran CSV at this path and rerun."
        )

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no headers")
        cols = detect_columns(reader.fieldnames)

        out: List[YearRecord] = []
        for row in reader:
            try:
                year = int(float(row[cols["year"]]))
            except Exception:
                continue
            if year < START_YEAR or year > END_YEAR:
                continue

            stock_nom = parse_percent(row[cols["stock"]])
            bond_nom = parse_percent(row[cols["bond"]])
            infl = parse_percent(row[cols["inflation"]])

            stock_real = (1.0 + stock_nom) / (1.0 + infl) - 1.0
            bond_real = (1.0 + bond_nom) / (1.0 + infl) - 1.0

            out.append(
                YearRecord(
                    year=year,
                    stock_nominal=stock_nom,
                    bond_nominal=bond_nom,
                    inflation=infl,
                    stock_real=stock_real,
                    bond_real=bond_real,
                )
            )

    out.sort(key=lambda r: r.year)
    expected_years = list(range(START_YEAR, END_YEAR + 1))
    got_years = [r.year for r in out]
    if got_years != expected_years:
        missing = sorted(set(expected_years) - set(got_years))
        extra = sorted(set(got_years) - set(expected_years))
        raise ValueError(
            f"Year coverage mismatch. Missing: {missing[:10]}{'...' if len(missing)>10 else ''}; "
            f"Extra: {extra[:10]}{'...' if len(extra)>10 else ''}"
        )

    return out


def contribution_for_year(idx: int) -> float:
    return 1.0 * (1.01 ** idx)


def stock_weight_for_year(idx: int) -> float:
    if HORIZON == 1:
        return 0.2
    return 0.9 + (0.2 - 0.9) * (idx / (HORIZON - 1))


def simulate_window(records: List[YearRecord], start_idx: int) -> CohortResult:
    w_stock = 0.0
    w_glide = 0.0
    start_year = records[start_idx].year
    end_year = records[start_idx + HORIZON - 1].year

    for t in range(HORIZON):
        rec = records[start_idx + t]
        contrib = contribution_for_year(t)

        # Contributions at start of year, then year return applies.
        w_stock = (w_stock + contrib) * (1.0 + rec.stock_real)

        sw = stock_weight_for_year(t)
        bw = 1.0 - sw
        port_r = sw * rec.stock_real + bw * rec.bond_real
        w_glide = (w_glide + contrib) * (1.0 + port_r)

    return CohortResult(
        start_year=start_year,
        end_year=end_year,
        terminal_stock_100=w_stock,
        terminal_glide=w_glide,
        glide_minus_stock=w_glide - w_stock,
    )


def summarize(results: List[CohortResult]) -> Dict[str, CohortResult]:
    best_stock = max(results, key=lambda r: r.terminal_stock_100)
    worst_stock = min(results, key=lambda r: r.terminal_stock_100)
    best_glide = max(results, key=lambda r: r.terminal_glide)
    worst_glide = min(results, key=lambda r: r.terminal_glide)
    return {
        "best_stock": best_stock,
        "worst_stock": worst_stock,
        "best_glide": best_glide,
        "worst_glide": worst_glide,
    }


def analyze_bond_safety(records: List[YearRecord]) -> Dict[str, float]:
    seventies = [r for r in records if 1970 <= r.year <= 1979]
    y2022 = next(r for r in records if r.year == 2022)
    return {
        "bond_real_1970s_avg": mean(r.bond_real for r in seventies),
        "bond_real_1970s_median": median(r.bond_real for r in seventies),
        "bond_real_2022": y2022.bond_real,
        "stock_real_2022": y2022.stock_real,
        "inflation_2022": y2022.inflation,
    }


def write_results_csv(results: List[CohortResult]) -> None:
    os.makedirs(os.path.dirname(RESULTS_CSV), exist_ok=True)
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "start_year",
                "end_year",
                "terminal_wealth_stock_100",
                "terminal_wealth_glidepath",
                "glide_minus_stock",
            ]
        )
        for r in results:
            w.writerow(
                [
                    r.start_year,
                    r.end_year,
                    f"{r.terminal_stock_100:.6f}",
                    f"{r.terminal_glide:.6f}",
                    f"{r.glide_minus_stock:.6f}",
                ]
            )


def make_svg(results: List[CohortResult], output_path: str) -> None:
    width, height = 1000, 520
    margin = 60

    xs = [r.start_year for r in results]
    y1 = [r.terminal_stock_100 for r in results]
    y2 = [r.terminal_glide for r in results]

    y_min = 0.0
    y_max = max(max(y1), max(y2)) * 1.05

    def x_to_px(x: float) -> float:
        return margin + (x - min(xs)) / (max(xs) - min(xs)) * (width - 2 * margin)

    def y_to_px(y: float) -> float:
        if y_max == y_min:
            return height - margin
        return height - margin - (y - y_min) / (y_max - y_min) * (height - 2 * margin)

    path1 = " ".join(
        f"{'M' if i==0 else 'L'} {x_to_px(xs[i]):.2f},{y_to_px(y1[i]):.2f}"
        for i in range(len(xs))
    )
    path2 = " ".join(
        f"{'M' if i==0 else 'L'} {x_to_px(xs[i]):.2f},{y_to_px(y2[i]):.2f}"
        for i in range(len(xs))
    )

    grid = []
    for i in range(6):
        yv = y_min + (y_max - y_min) * i / 5
        py = y_to_px(yv)
        grid.append(f'<line x1="{margin}" y1="{py:.2f}" x2="{width-margin}" y2="{py:.2f}" stroke="#eee"/>')
        grid.append(f'<text x="10" y="{py+4:.2f}" font-size="12">{yv:.1f}</text>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
<rect width="100%" height="100%" fill="white"/>
<text x="{width/2:.0f}" y="24" text-anchor="middle" font-size="18" font-weight="bold">Terminal Wealth by Cohort (Real)</text>
{''.join(grid)}
<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="black"/>
<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="black"/>
<path d="{path1}" fill="none" stroke="#1f77b4" stroke-width="2"/>
<path d="{path2}" fill="none" stroke="#ff7f0e" stroke-width="2"/>
<text x="{margin}" y="{height-20}" font-size="12">{min(xs)}</text>
<text x="{width-margin-20}" y="{height-20}" font-size="12">{max(xs)}</text>
<rect x="{width-280}" y="40" width="12" height="12" fill="#1f77b4"/><text x="{width-260}" y="50" font-size="12">100% Stocks</text>
<rect x="{width-280}" y="60" width="12" height="12" fill="#ff7f0e"/><text x="{width-260}" y="70" font-size="12">Glide path</text>
</svg>'''

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)


def write_report(results: List[CohortResult], stats: Dict[str, CohortResult], bond_stats: Dict[str, float]) -> None:
    avg_stock = mean(r.terminal_stock_100 for r in results)
    avg_glide = mean(r.terminal_glide for r in results)
    better_glide = sum(1 for r in results if r.terminal_glide > r.terminal_stock_100)

    lines = [
        "# Sequencing Risk Analysis Results",
        "",
        "## Setup",
        "- Data window: 1945-2024 annual returns.",
        "- Contributions: 1.0 in year 1, then +1% real annually for 46 years.",
        "- Timing: contribution at start of year; annual real return then applies.",
        "",
        "## Cohort outcomes",
        f"- Number of cohorts: {len(results)}",
        f"- Mean terminal wealth (100% stocks): {avg_stock:.2f}",
        f"- Mean terminal wealth (glide path): {avg_glide:.2f}",
        f"- Glide path beat 100% stocks in {better_glide}/{len(results)} cohorts.",
        "",
        "### Best and worst cohorts",
        f"- Best 100% stocks: {stats['best_stock'].start_year}-{stats['best_stock'].end_year}, terminal wealth={stats['best_stock'].terminal_stock_100:.2f}",
        f"- Worst 100% stocks: {stats['worst_stock'].start_year}-{stats['worst_stock'].end_year}, terminal wealth={stats['worst_stock'].terminal_stock_100:.2f}",
        f"- Best glide path: {stats['best_glide'].start_year}-{stats['best_glide'].end_year}, terminal wealth={stats['best_glide'].terminal_glide:.2f}",
        f"- Worst glide path: {stats['worst_glide'].start_year}-{stats['worst_glide'].end_year}, terminal wealth={stats['worst_glide'].terminal_glide:.2f}",
        "",
        "## Bond safety analysis",
        f"- 1970s average real bond return: {bond_stats['bond_real_1970s_avg']*100:.2f}%.",
        f"- 1970s median real bond return: {bond_stats['bond_real_1970s_median']*100:.2f}%.",
        f"- 2022 real bond return: {bond_stats['bond_real_2022']*100:.2f}%.",
        f"- 2022 real stock return: {bond_stats['stock_real_2022']*100:.2f}%.",
        f"- 2022 inflation: {bond_stats['inflation_2022']*100:.2f}%.",
        "",
        "Interpretation: bonds were not consistently a safe real asset in high-inflation or rate-shock environments.",
    ]

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    records = load_records(INPUT_PATH)
    results = [simulate_window(records, i) for i in range(0, len(records) - HORIZON + 1)]
    stats = summarize(results)
    bond_stats = analyze_bond_safety(records)

    write_results_csv(results)
    make_svg(results, SVG_PATH)
    write_report(results, stats, bond_stats)

    print(f"Wrote {RESULTS_CSV}, {SVG_PATH}, {REPORT_MD}")


if __name__ == "__main__":
    main()
