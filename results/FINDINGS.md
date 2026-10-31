# Bain (1951) on modern data: findings

## In plain English

In 1951 Joe Bain showed that American manufacturing industries dominated by a few companies, where the top 8
made 70%+ of sales, earned far higher profits than other industries: 12% vs. 7% a year. This study reruns his test
on 2015–2025 data.

- **His pattern has disappeared.** Highly concentrated industries range from very profitable (tobacco: Philip
  Morris, Altria; chip-making equipment: Applied Materials, Lam Research) to loss-making (aircraft: Boeing;
  batteries: EnerSys, Energizer). On average they earn about what everyone else does.
- **Apparent pricing power mostly reflects R&D.** Drug and biotech makers (Pfizer, Merck, AbbVie, Amgen) look
  like they charge the biggest markups because research and marketing aren't counted as production costs. Count
  them and concentrated industries look the same as the rest.
- **Consolidation does favor the biggest players.** In industries that became more concentrated between 2017 and
  2022, such as steel (Nucor, Cleveland-Cliffs), refining (ExxonMobil, Chevron, Marathon) and semiconductors
  (Nvidia, Intel), profits rose on average. The gains went to the largest companies while smaller rivals' profits
  fell, which looks more like strong companies pulling ahead than like coordinated price-raising. Steel and
  refining also had price booms in 2021–22, so not all of that rise is about concentration.

A friendlier tour with more examples is in the [README](../README.md). The rest of this page is the technical
detail.

**Key to the labels below:** *Window A* = 2017 Census concentration with fiscal 2015–19 profits. *Window B* =
2022 Census concentration with fiscal 2021–25 profits. *CR8* = the share of industry sales made by the 8 largest
companies.

## Summary

**Question (Bain's):** Do manufacturing industries where a few firms dominate earn higher profit rates?

**Answer for 2015–2025: not in Bain's sense, but there's a within-industry link.**

- **Comparing industries (Bain's test):** no. His 70% threshold doesn't reappear in either modern period, under any
  of four profit measures or three markup measures, and no other cutoff gives a stable break.
- **Comparing each industry with itself, 2017 → 2022:** where concentration rose, profits tended to rise too. This
  is clear when big industries count more, and positive but not statistically significant when every industry counts
  equally. At the firm level the gains went to the largest firms, while smaller firms' profits slipped. That's the
  "superstar firm" pattern rather than collusion. See [Concentration changes](#concentration-changes-2017--2022).

Full tables are in [REPORT.md](REPORT.md) and [CHANGES.md](CHANGES.md).

## Bain's test, side by side

Industry average profit rate, industries above vs. below an 8-firm concentration ratio of 70%:

| | Industries (above / below) | ROE above 70 | ROE below 70 | Gap | p |
|---|---|---|---|---|---|
| **Bain: 1935 concentration, 1936–40 profits** | 22 / 20 | 12.1% | 6.9% | **+5.2** | **< 0.001** |
| **Window A: 2017 concentration, FY2015–19** | 22 / 81 | 18.5% | 14.1% | +4.4 | 0.54 |
| **Window B: 2022 concentration, FY2021–25** | 20 / 68 | 12.4% | 13.9% | −1.5 | 0.77 |

Other profit measures, same split:

| | Window A gap | p | Window B gap | p |
|---|---|---|---|---|
| Return on assets | +0.4 | 0.77 | +0.5 | 0.76 |
| Operating return on assets | −0.4 | 0.79 | −0.3 | 0.88 |
| Price-cost margin | +1.4 | 0.54 | −1.3 | 0.63 |

Window A's ROE gap is about the size of Bain's, but it isn't real. It comes mostly from tobacco (157% ROE: Altria
and Philip Morris have shrunk their book equity with buybacks and dividends), and it vanishes in ROA, which
buybacks can't distort.

## The other tests

- **Continuous concentration:** each extra point of CR8 adds 0.17 points of ROE (p = 0.36) in window A and 0.11
  (p = 0.29) in window B. ROA slopes are about zero. Controls for capital, R&D and advertising intensity, which are
  proxies for Bain's later "barriers to entry," don't change this.
- **Is there a different threshold?** Scanning every cutoff from 24% to 86% gives a best split of 53% in window A
  (z = 1.19) and 55% in window B (z = 2.06). With about 70 cutoffs tested, one z near 2 is expected by luck, and the
  two periods don't agree.
- **Bain's Table IV pattern (only big firms gain):** the largest firms (Bain's top size class in today's dollars,
  over ~$850M–975M of equity) do show higher ROE in concentrated industries (+1.4 and +5.5 points), but it's not
  significant (p = 0.80, 0.33), and it mostly disappears in ROA. These firms carry less equity (30–37% of assets vs.
  42%), which mechanically raises ROE.
- **Demsetz's test:** small firms in concentrated industries don't earn more. Their ROA slope on concentration is
  slightly negative (−0.24, p = 0.13; −0.16, p = 0.21). Collusion would predict a positive slope. But the largest
  firms' slope is also flat, so this isn't Demsetz's efficiency pattern either. Concentration just doesn't line up with
  profitability here.

## Markups instead of profits

Following De Loecker, Eeckhout & Unger (2020, "DEU"), a firm's markup (price over marginal cost) is
**θ × sales / cost of goods sold**, where θ is the output elasticity of variable inputs. Markups avoid the
balance-sheet problems with ROE (book equity, buybacks, unrecorded intangibles).

| Industry markup, above vs. below CR8 = 70 | Window A gap | p | Window B gap | p |
|---|---|---|---|---|
| COGS-based, cost-share θ (DEU's robustness method) | −0.25 | 0.09 | −0.25 | 0.14 |
| COGS-based, θ fixed at 0.85 | −0.23 | 0.09 | −0.24 | 0.14 |
| COGS + SG&A as the cost (Traina 2018) | −0.01 | 0.85 | −0.03 | 0.61 |
| COGS-based, regression slope with R&D/advertising/capital controls | −0.0005 per CR8 point | 0.88 | −0.0004 | 0.89 |

- **COGS-based markups are *lower* in concentrated industries, but only because of what's in COGS.** COGS leaves
  out R&D and SG&A, so R&D-heavy industries (pharma, biotech, medical devices), which are mostly below 70%
  concentration, look like they charge huge markups. Controlling for R&D and advertising intensity explains about
  60% of the variation in industry markups and takes the concentration slope to zero.
- **Counting SG&A as a cost** gives markups around 1.2, in line with Traina's estimates, and no difference at all
  between concentrated and unconcentrated industries.
- **The trend:** COGS-based manufacturing markups rose from 1.75 (2013) to 1.99 (2025). All of the rise came in the
  *less* concentrated industries (1.84 → 2.19). The concentrated ones drifted down (1.51 → 1.41). With SG&A counted,
  the rise is smaller: 1.18 → 1.28. See [markup_trend.png](markup_trend.png).

**The headline doesn't change:** concentration doesn't predict markups any more than it predicts profits.

**Why there's no production-function θ:** DEU's main estimates of θ come from estimating production functions
(the Ackerberg–Caves–Frazer method). I built that and tested it on simulated firms with a known θ of 0.70. It
returned about 0.90, and about 1.0 with no noise at all, because θ = 1 also satisfies the method's moment
conditions when COGS is the flexible input. This is the identification problem raised by Gandhi, Navarro &
Rivers (2020) and Bond, Hashemi, Kaplan & Zoch (2021). Since it couldn't recover a known answer, it isn't
reported.

## Concentration changes, 2017 → 2022

Comparing each industry with itself removes anything fixed about it: R&D intensity, accounting conventions,
unrecorded intangibles. That deals with most of the problems with the cross-industry comparisons above. Only
industries whose NAICS definition didn't change are used.

**How much did concentration move?** Very little on average. Across 330 manufacturing industries, the 8-firm ratio
rose by 0.4 points, going up in 56% of them. Most moved between −6 and +6 points.

**Industry level** (74 industries in both samples). Slope = change in the measure per 1-point rise in CR8:

| Measure | Slope, industries equal | p | Slope, weighted by shipments | p |
|---|---|---|---|---|
| ROA (%) | +0.17 | 0.12 | **+0.44** | **0.001** |
| Operating ROA (%) | +0.17 | 0.13 | **+0.52** | **0.014** |
| ROE (%) | +0.46 | 0.09 | **+1.12** | **0.003** |
| Price-cost margin (%) | **+0.15** | **0.03** | +0.20 | 0.10 |
| Markup, COGS + SG&A | **+0.0024** | **0.02** | +0.0026 | 0.22 |
| Markup, COGS (cost share) | +0.005 | 0.20 | +0.008 | 0.07 |

- **Every sign is positive.** Industries where concentration rose saw profits and markups rise. In the weighted
  version, a 5-point rise in CR8 goes with about 2 points more ROA, which is large next to typical ROA of about 5%.
- **It isn't one industry.** Refineries carry 23% of the shipment weight and had a 2022 fuel-price windfall. Dropping
  them still leaves +0.31 (p = 0.03), and dropping any single industry leaves the slope between +0.31 and +0.48.
- **It's weaker when every industry counts equally:** positive, but mostly not significant. The link is concentrated
  in large industries.

**Firm level** (564 firms in the same industry in both periods, so changes in which firms are listed don't matter):

| ROA change per 1-point rise in CR8 | Slope | p |
|---|---|---|
| Smaller firms (bottom three size quartiles) | −0.81 | 0.07 |
| Extra for the largest quartile | +0.97 | 0.04 |
| Net for the largest firms | about +0.15 | |

Operating ROA shows the same split. This is Demsetz's prediction and the "superstar firms" story (Autor et al. 2020):
when concentration rises, big firms gain while small firms lose ground. Collusion would lift small firms' profits
too. The p-values here are borderline, so treat it as suggestive.

**Caveats specific to this test:**

- **Only two snapshots** (2017 and 2022 Censuses), and the 2021–25 window includes the post-COVID commodity boom.
  Steel and refining had both concentration increases and price windfalls.
- **Concentration changes aren't random.** Mergers, exits and booms move both concentration and profits. This is an
  association, not proof that concentration caused anything.
- **The changes are small and noisy,** which usually biases slopes toward zero.

See [CHANGES.md](CHANGES.md) and [changes_scatter.png](changes_scatter.png).

## How to read this

**What it does say:** among US-listed manufacturers, accounting profit rates in 2015–2025 were not higher in highly
concentrated industries. That's true by Bain's own method and with the modern robustness checks. Within industries
over time, rising concentration did go with rising profits, mainly for the largest firms.

**What it doesn't say:** that market power doesn't exist. Several modern features make this test weaker than in 1951:

1. **Profits aren't measured where concentration is.** Census concentration counts US plants. Compustat profits are
   global, company-wide earnings: Apple or Pfizer earn most of theirs outside US manufacturing.
2. **Imports aren't counted.** Census ratios ignore foreign competition, so autos look 85–90% concentrated even
   though Toyota, Hyundai and others sell heavily here. The import adjustment is built in but needs a Census API key.
3. **Intangibles are off the balance sheet.** R&D and brands aren't counted as assets, so returns in pharma, tech and
   consumer brands are overstated, and unevenly.
4. **Public companies only.** Small private manufacturers, which dominate unconcentrated industries, aren't in
   Compustat.
5. **Accounting returns aren't economic returns.** This is Bain's own caveat, and it's worse with buybacks and
   negative equity.

These are the critiques that moved IO away from cross-industry studies after the 1970s. Markups fix the
balance-sheet problems (point 5) but not the others, and they bring a new one: the answer depends on which costs
count as variable.

**One more contrast with Bain:** his result only became significant after he cut 149 industries down to 42, and he
admitted the dropped ones showed the opposite pattern. Here, every filter (3+ firms, one main industry, national
markets, $10M+ sales) was written into the code before seeing results and applied the same way to both periods.

## Sample

| | Window A | Window B |
|---|---|---|
| Census concentration year | 2017 | 2022 |
| Fiscal years | 2015–2019 | 2021–2025 |
| Industries (6-digit NAICS) | 103 | 88 |
| Firms | 992 | 1,002 |

Data: US Census Bureau Economic Census concentration tables; Compustat North America Fundamentals Annual and
Historical Segments via WRDS (accessed 2026-10-31).

## Possible next steps

- Add the import adjustment (needs a free Census API key).
- Extend the changes test back to the 2012 and 2007 Censuses for more snapshots, which would help separate
  concentration from one-off booms.
