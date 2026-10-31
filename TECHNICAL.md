# Technical notes

This is the technical companion to the [README](README.md). It covers the data, method, the full set of tests and
how to reproduce everything. The complete results, with test statistics, are in
[results/FINDINGS.md](results/FINDINGS.md). Every table is in [results/REPORT.md](results/REPORT.md) and
[results/CHANGES.md](results/CHANGES.md).

## The original study

Joe S. Bain, "Relation of Profit Rate to Industry Concentration: American Manufacturing, 1936–1940,"
*Quarterly Journal of Economics* 65(3), 1951, pp. 293–324. Bain paired 1935 Census eight-firm concentration
ratios with 1936–40 SEC profit data for 42 industries (335 firms) and found that industries with CR8 ≥ 70% earned
12.1% on equity vs. 6.9% below the line (p < 0.001). The relationship looked like a step at 70%, not a straight
line (r = 0.33).

## Headline results

| | Industries (above / below 70%) | ROE above | ROE below | Gap | p |
|---|---|---|---|---|---|
| Bain: 1935 concentration, 1936–40 profits | 22 / 20 | 12.1% | 6.9% | +5.2 | < 0.001 |
| 2017 concentration, FY2015–19 | 22 / 81 | 18.5% | 14.1% | +4.4 | 0.54 |
| 2022 concentration, FY2021–25 | 20 / 68 | 12.4% | 13.9% | −1.5 | 0.77 |

- No significant gap in ROE, ROA, operating ROA or price-cost margins in either window. A scan of every cutoff
  from 24% to 86% finds no break that holds in both windows.
- COGS-based markups (De Loecker, Eeckhout & Unger 2020) are *lower* above the line, a composition effect from
  R&D-intensive industries. Controlling for R&D and advertising intensity takes the slope to zero, and treating
  COGS + SG&A as the variable input (Traina 2018) removes the gap.
- Within industries, ΔCR8 (2017→2022) is positively related to ΔROA: +0.44 per point, shipment-weighted,
  p = 0.001, robust to leave-one-out (+0.31 to +0.48). Unweighted it's +0.17 (p = 0.12). At the firm level,
  smaller firms' ROA falls with ΔCR8 (−0.81, p = 0.07) and the largest quartile's rises relative to them
  (+0.97, p = 0.04), consistent with Demsetz (1973) and the superstar-firm account (Autor et al. 2020).

## Data

- **Concentration:** US Census Bureau, 2017 and 2022 Economic Census concentration tables (`EC1700SIZECONCEN`,
  `EC2200SIZECONCEN`): CR4, CR8, CR20, CR50 and HHI (top 50 firms) for 6-digit NAICS manufacturing industries.
  Codes that changed between NAICS 2017 and 2022 are bridged with the Census concordance.
- **Profits:** Compustat North America Fundamentals Annual (FY2013–2025) and Historical Segments (2014–2026), via
  WRDS. US-headquartered firms only.

## Method

- **Windows:** 2017 concentration with FY2015–19 profits; 2022 concentration with FY2021–25 profits. This mirrors
  Bain's pairing of the 1935 Census with 1936–40 profits.
- **Profit measures:** net income / beginning-of-year common equity (Bain's measure; firm-years with non-positive
  lagged equity excluded); net income / lagged total assets; operating income after depreciation / lagged assets;
  (sales − COGS − SG&A) / sales.
- **Bain's industry averages:** within each year, sum of firm profits / sum of firm denominators (size-weighted);
  then the simple average across years. Each ratio uses only firm-years where both numerator and denominator exist.
- **Sample rules, fixed before seeing results:** industries need profit data for ≥ 3 firms; firm-years with
  < 2/3 of segment sales in one 6-digit NAICS industry are dropped (Bain's "substantial majority" rule; product-line
  segments, BUSSEG with OPSEG as fallback, original filings only); firms need ≥ 3 of 5 window years and ≥ $10M
  average sales; a judgment list of local- and regional-market industries (ready-mix concrete, bakeries, cement,
  brick, etc.) is excluded.
- **Significance:** Bain's large-sample z-test for differences in group means; WLS with HC1 errors for
  net-worth-weighted firm comparisons; firm-level regressions clustered by industry.
- **Regressions:** industry-level OLS with HC1 errors and entry-barrier proxies (capital intensity, R&D intensity,
  advertising intensity, plus import share when available).
- **Markups:** μ = θ × sales / COGS. θ is the industry-year (3-digit NAICS) median of COGS / (COGS + rK), with
  user cost r = fed funds − CPI inflation + 12% depreciation and K = gross PP&E; alternatively θ = 0.85, or COGS + SG&A
  as the variable input with its own cost share. The sales/COGS ratio is trimmed at 1%/99%; industry markups are
  sales-weighted.
- **Why no production-function θ:** an Ackerberg–Caves–Frazer estimator was implemented and tested on simulated
  Cobb–Douglas firms with θ = 0.70. It returned about 0.90, and about 1.0 without noise, because θ = 1 also
  satisfies the moment conditions when COGS is the flexible input (Gandhi, Navarro & Rivers 2020; Bond, Hashemi,
  Kaplan & Zoch 2021). It was dropped.
- **Within-industry test:** industries with an unchanged (1:1) NAICS definition across 2017 and 2022. ΔCR8 against
  Δ profit and markup measures, winsorized 5%/95%, equal- and shipment-weighted. The firm-level version uses firms in
  the same industry in both windows, with Δ measures winsorized 1%/99% and an interaction with a top-asset-quartile
  dummy.
- **Import adjustment (implemented, not run):** CR8 × (S − X) / (S − X + M) using Census trade data; requires a
  Census API key.

## Reproducing the results

1. Pull the two Compustat extracts in [DATA_TO_GET.md](DATA_TO_GET.md) into `data/compustat/`.
2. Install the packages (Python 3.12+):

   ```bash
   pip install -r requirements.txt
   ```

3. Run:

   ```bash
   python src/bain_modern.py --compustat data/compustat/funda_2013_2026.csv.zip --segments data/compustat/segments_hist_2014_2026.csv.zip
   python src/concentration_changes.py
   ```

   Add `--census-key-file path/to/key.txt` to the first command for the import adjustment.

## Repository layout

| Path | What it is |
|---|---|
| [src/bain_modern.py](src/bain_modern.py) | Sample construction, Bain's test, threshold scan, Demsetz test, regressions, markups |
| [src/concentration_changes.py](src/concentration_changes.py) | Within-industry changes, 2017 → 2022 |
| [results/FINDINGS.md](results/FINDINGS.md) | Full results write-up |
| [results/REPORT.md](results/REPORT.md), [results/CHANGES.md](results/CHANGES.md) | All tables |
| `results/industries_*.csv`, `results/changes_industries.csv` | Industry-level results |
| `data/raw/` | Census concentration tables and NAICS concordance |

## Licensing

Census data is public domain. Compustat is licensed through WRDS and is not redistributed. Only industry-level
aggregates appear in `results/`.

## References

- Azar, J., Schmalz, M. & Tecu, I. (2018). Anticompetitive effects of common ownership. *Journal of Finance*
  73(4).
- Autor, D., Dorn, D., Katz, L., Patterson, C. & Van Reenen, J. (2020). The fall of the labor share and the rise
  of superstar firms. *QJE* 135(2).
- Bain, J. S. (1951). Relation of profit rate to industry concentration. *QJE* 65(3).
- Bain, J. S. (1956). *Barriers to New Competition*. Harvard University Press.
- Bond, S., Hashemi, A., Kaplan, G. & Zoch, P. (2021). Some unpleasant markup arithmetic. *Journal of Monetary
  Economics* 121.
- De Loecker, J., Eeckhout, J. & Unger, G. (2020). The rise of market power and the macroeconomic implications.
  *QJE* 135(2).
- Demsetz, H. (1973). Industry structure, market rivalry, and public policy. *Journal of Law and Economics* 16(1).
- Fichtner, J., Heemskerk, E. & Garcia-Bernardo, J. (2017). Hidden power of the Big Three? *Business and
  Politics* 19(2).
- Gandhi, A., Navarro, S. & Rivers, D. (2020). On the identification of gross output production functions.
  *Journal of Political Economy* 128(8).
- Schmalensee, R. (1989). Inter-industry studies of structure and performance. *Handbook of Industrial
  Organization*, Vol. 2.
- Traina, J. (2018). Is aggregate market power increasing? Production trends using financial statements.
  Stigler Center Working Paper.
