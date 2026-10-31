"""Within-industry version of Bain's test: did profits and markups rise where concentration rose?

Compares each industry with itself: CR8 from the 2017 to the 2022 Economic Census against the change
in profit rates and markups from FY2015-19 to FY2021-25. Anything fixed about an industry (R&D
intensity, accounting conventions, unrecorded intangibles) differences out.

Run src/bain_modern.py first; this reads its industries_*.csv and firms_*.csv.

Usage:
    python src/concentration_changes.py
"""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

import bain_modern as b

MEASURES = {
    "roe": "ROE (%)",
    "roa": "ROA (%)",
    "oroa": "Operating ROA (%)",
    "pcm": "Price-cost margin (%)",
    "mu_cs": "Markup, COGS (cost share)",
    "mu_opex": "Markup, COGS + SG&A",
}


def one_to_one(concordance):
    """2017 -> 2022 NAICS pairs where neither side was split or merged."""
    c = concordance.drop_duplicates()
    c = c[c.groupby("n17").n22.transform("size").eq(1) & c.groupby("n22").n17.transform("size").eq(1)]
    return c.set_index("n17").n22


def census_changes(mapping):
    """CR8 change for every manufacturing industry with an unchanged definition."""
    c17, c22 = b.load_concentration(2017), b.load_concentration(2022)
    d = c17[["label", "cr8", "hhi", "shipments"]].join(mapping.rename("n22"), how="inner")
    d = d.join(c22[["cr8", "hhi", "shipments"]], on="n22", suffixes=("", "_22"), how="inner")
    d["d_cr8"] = d.cr8_22 - d.cr8
    return d


def fit(formula, data, groups=None, weights=None):
    model = smf.wls(formula, data=data, weights=weights) if weights is not None else smf.ols(formula, data=data)
    kw = dict(cov_type="cluster", cov_kwds={"groups": groups}) if groups is not None else dict(cov_type="HC1")
    return model.fit(**kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(b.OUT))
    args = ap.parse_args()
    res = Path(args.results)

    mapping = one_to_one(b.load_concordance())
    census = census_changes(mapping)

    ia = pd.read_csv(res / "industries_A.csv", dtype={"naics": str}).set_index("naics")
    ib = pd.read_csv(res / "industries_B.csv", dtype={"naics": str}).set_index("naics")
    ind = ia.join(mapping.rename("n22"), how="inner").join(ib, on="n22", suffixes=("", "_22"), how="inner")
    for m in list(MEASURES) + ["cr8"]:
        ind[f"d_{m}"] = ind[f"{m}_22"] - ind[m]
    ind.to_csv(res / "changes_industries.csv")

    fa = pd.read_csv(res / "firms_A.csv", dtype={"gvkey": str, "naics": str}).set_index("gvkey")
    fb = pd.read_csv(res / "firms_B.csv", dtype={"gvkey": str, "naics": str}).set_index("gvkey")
    firm = fa.join(fb, suffixes=("", "_22"), how="inner")
    firm["n22"] = firm.naics.map(mapping)
    firm = firm[firm.naics_22 == firm.n22]  # same industry in both periods
    firm["d_cr8"] = firm.cr8_22 - firm.cr8
    for m in MEASURES:
        firm[f"d_{m}"] = b.winsorize(firm[f"{m}_22"] - firm[m])
    firm["large"] = (firm.assets >= firm.assets.quantile(0.75)).astype(int)
    firm.to_csv(res / "changes_firms.csv")

    r = ["# Concentration changes vs. profit and markup changes\n",
         "Each industry compared with itself: CR8 from the 2017 to the 2022 Economic Census, against profit rates "
         "and markups from FY2015–19 to FY2021–25. Only industries whose NAICS definition didn't change.\n"]

    r.append("## How concentration changed, all manufacturing\n")
    up = (census.d_cr8 > 0).mean()
    wavg = np.average(census.d_cr8, weights=census.shipments)
    r.append(f"Across {len(census)} manufacturing industries with unchanged definitions, CR8 changed by "
             f"{census.d_cr8.mean():+.1f} points on average ({wavg:+.1f} weighted by shipments). "
             f"It rose in {up:.0%} of industries. Median change {census.d_cr8.median():+.1f}; "
             f"10th–90th percentile {census.d_cr8.quantile(0.1):+.1f} to {census.d_cr8.quantile(0.9):+.1f}.\n")
    show = census.sort_values("d_cr8")
    cols = ["label", "cr8", "cr8_22", "d_cr8"]
    r.append("Largest increases:\n")
    r.append(show.tail(8)[cols].iloc[::-1].round(1).to_markdown())
    r.append("\nLargest decreases:\n")
    r.append(show.head(8)[cols].round(1).to_markdown())
    r.append("")

    r.append(f"## Industry level ({len(ind)} industries in both samples)\n")
    r.append("Slope = change in the measure per 1-point rise in CR8. Robust standard errors.\n")
    r.append("| Measure | Mean change | Slope | SE | p | Slope, shipment-weighted | p |")
    r.append("|---|---|---|---|---|---|---|")
    for m, label in MEASURES.items():
        d = ind.dropna(subset=[f"d_{m}", "d_cr8"])
        d = d.assign(y=b.winsorize(d[f"d_{m}"], 0.05))  # small sample: trim extreme industries at 5%
        f1 = fit("y ~ d_cr8", d)
        f2 = fit("y ~ d_cr8", d, weights=d.shipments)
        r.append(f"| {label} | {d[f'd_{m}'].median():+.3f} (median) | {f1.params['d_cr8']:+.4f} | "
                 f"{f1.bse['d_cr8']:.4f} | {f1.pvalues['d_cr8']:.3f} | {f2.params['d_cr8']:+.4f} | "
                 f"{f2.pvalues['d_cr8']:.3f} |")
    r.append("\nIndustry changes are winsorized at 5%/95% because the sample is small.\n")

    # Shipment weights are lopsided (refineries alone are ~a fifth), so check no single industry drives it
    d = ind.dropna(subset=["d_roa", "d_cr8"]).assign(y=lambda x: b.winsorize(x.d_roa, 0.05))
    top = d.shipments.idxmax()
    loo = pd.Series({code: fit("y ~ d_cr8", d.drop(index=code), weights=d.drop(index=code).shipments)
                     .params["d_cr8"] for code in d.index})
    no_top = fit("y ~ d_cr8", d.drop(index=top), weights=d.drop(index=top).shipments)
    r.append(f"**Robustness (shipment-weighted ROA slope):** the largest industry, {d.label[top].lower()}, carries "
             f"{d.shipments[top] / d.shipments.sum():.0%} of the weight. Without it the slope is "
             f"{no_top.params['d_cr8']:+.3f} (p = {no_top.pvalues['d_cr8']:.3f}). Dropping any single industry "
             f"leaves it between {loo.min():+.3f} and {loo.max():+.3f}.\n")

    r.append(f"## Firm level ({len(firm)} firms in the same industry in both periods)\n")
    r.append("Same firms in both periods, so changes in which firms are listed don't matter. "
             "Standard errors clustered by industry.\n")
    r.append("| Measure | Slope (all firms) | p | Slope, smaller firms | p | Extra slope, largest quartile | p |")
    r.append("|---|---|---|---|---|---|---|")
    # Firm-level price-cost margins are dominated by small loss-makers at -1,000% and worse
    for m, label in ((m, l) for m, l in MEASURES.items() if m != "pcm"):
        d = firm.dropna(subset=[f"d_{m}", "d_cr8"])
        f1 = fit(f"d_{m} ~ d_cr8", d, groups=d.naics)
        f2 = fit(f"d_{m} ~ d_cr8 * large", d, groups=d.naics)
        r.append(f"| {label} | {f1.params['d_cr8']:+.4f} | {f1.pvalues['d_cr8']:.3f} | "
                 f"{f2.params['d_cr8']:+.4f} | {f2.pvalues['d_cr8']:.3f} | "
                 f"{f2.params['d_cr8:large']:+.4f} | {f2.pvalues['d_cr8:large']:.3f} |")
    r.append("\nIf rising concentration made collusion easier, small firms' profits should rise along with large "
             "firms'. If it reflected efficient firms winning share, only the large firms should gain.\n")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, m in zip(axes, ["roa", "mu_opex"]):
        d = ind.dropna(subset=[f"d_{m}", "d_cr8"])
        y = b.winsorize(d[f"d_{m}"], 0.05)
        ax.scatter(d.d_cr8, y, color="#2a6fdb", alpha=0.7)
        slope, icept = np.polyfit(d.d_cr8, y, 1)
        xs = np.linspace(d.d_cr8.min(), d.d_cr8.max(), 2)
        ax.plot(xs, icept + slope * xs, color="#c0392b", lw=1.5)
        ax.axhline(0, color="#999999", lw=0.8)
        ax.axvline(0, color="#999999", lw=0.8)
        ax.set_xlabel("Change in CR8, 2017 to 2022 (points)")
        ax.set_ylabel(f"Change in {MEASURES[m]}")
        ax.set_title(MEASURES[m])
    fig.suptitle("Within-industry changes: concentration vs. profitability")
    fig.tight_layout()
    fig.savefig(res / "changes_scatter.png", dpi=150)
    plt.close(fig)
    r.append("![changes](changes_scatter.png)\n")

    (res / "CHANGES.md").write_text("\n".join(r), encoding="utf-8")
    print("\n".join(r))


if __name__ == "__main__":
    main()
