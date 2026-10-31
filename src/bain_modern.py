"""Bain (1951) on modern data: profit rates vs. seller concentration in US manufacturing.

Bain paired 1935 Census concentration ratios with 1936-40 SEC profits. We do the
same twice, pairing each Economic Census with the five fiscal years around it:

    Window A: 2017 Census concentration, FY2015-2019 profits
    Window B: 2022 Census concentration, FY2021-2025 profits

Usage:
    python src/bain_modern.py --compustat FUNDA.csv [--segments SEG.csv] [--census-key-file KEY.txt]
"""

import argparse
import json
import urllib.request
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "results"

WINDOWS = {
    "A": dict(census=2017, years=list(range(2015, 2020))),
    "B": dict(census=2022, years=list(range(2021, 2026))),
}
BAIN_LINE = 70.0
MIN_FIRMS = 3          # Bain dropped industries with profit data for fewer than three firms
MIN_YEARS = 3          # firm needs at least 3 of the 5 window years
MIN_SALES = 10         # average annual sales, $ millions
PRIMARY_SHARE = 2 / 3  # Bain's "substantial majority" of a firm's business in one industry
WINSOR = 0.01          # Bain dropped 2 of 335 firms (0.6%) as outliers; we winsorize 1%/99%

# CPI-U annual averages, to express Bain's 1936 net-worth classes in window dollars
CPI = {1936: 13.9, 2015: 237.0, 2021: 271.0}

# User cost of capital for cost-share markups, as in DEU (2020): nominal rate - inflation + 12%
# depreciation. Effective federal funds rate and CPI-U inflation, annual averages, percent
# (2025 values approximate).
FED_FUNDS = {2012: 0.14, 2013: 0.11, 2014: 0.09, 2015: 0.13, 2016: 0.40, 2017: 1.00, 2018: 1.83,
             2019: 2.16, 2020: 0.38, 2021: 0.08, 2022: 1.68, 2023: 5.02, 2024: 5.14, 2025: 4.20}
INFLATION = {2012: 2.1, 2013: 1.5, 2014: 1.6, 2015: 0.1, 2016: 1.3, 2017: 2.1, 2018: 2.4,
             2019: 1.8, 2020: 1.2, 2021: 4.7, 2022: 8.0, 2023: 4.1, 2024: 2.9, 2025: 2.7}
DEPRECIATION = 0.12
THETA_FIXED = 0.85  # DEU's average output elasticity of variable inputs

# Industries whose national CR8 badly understates true (local) concentration. Bain
# dropped "regional" and "local" industries using the NRC classification; no modern
# equivalent exists, so this is a judgment list of high transport-cost products.
LOCAL_MARKET_NAICS = {
    "311811", "311812",            # bakeries
    "311511",                      # fluid milk
    "312113",                      # ice
    "323111",                      # commercial printing
    "324121",                      # asphalt paving mixtures
    "327121",                      # brick and structural clay tile
    "327310",                      # cement
    "327320",                      # ready-mix concrete
    "327331", "327332", "327390",  # concrete block, pipe, other concrete products
}

# Bain (1951) Table I: (8-firm concentration ratio 1935, industry average profit rate 1936-40)
BAIN_TABLE_I = [
    (100.0, 9.0), (99.4, 14.4), (99.3, 15.8), (97.3, 16.9), (95.0, 9.3), (94.2, 16.3),
    (90.4, 8.2), (90.2, 12.1), (87.7, 9.1), (86.4, 10.1), (85.6, 9.1), (84.9, 12.9),
    (84.3, 11.7), (84.0, 2.8), (83.7, 9.7), (83.1, 15.2), (82.8, 12.3), (82.2, 4.7),
    (79.7, 14.0), (72.8, 20.8), (71.4, 14.2), (68.2, 7.4), (68.2, 4.7), (63.8, 4.9),
    (63.5, 3.6), (63.0, 8.6), (58.9, 6.8), (54.0, 7.5), (54.0, 1.8), (50.7, 6.9),
    (49.0, 18.3), (47.4, 2.2), (44.7, 5.4), (37.0, 7.6), (34.3, 0.8), (32.9, 8.2),
    (30.8, 7.5), (30.4, 7.4), (27.1, 8.4), (23.7, 12.4), (19.9, 17.0), (7.6, 9.1),
]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def read_any(path):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".sas7bdat":
        return pd.read_sas(path, encoding="latin-1")
    if suffix == ".dta":
        return pd.read_stata(path)
    return pd.read_csv(path, low_memory=False)


def naics6(series):
    """Normalize NAICS codes (strings, floats like 336111.0) to 6-digit strings, else NaN."""
    s = series.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    return s.where(s.str.fullmatch(r"\d{6}"))


def load_concentration(year):
    yy = str(year)[2:]
    df = pd.read_csv(RAW / f"EC{yy}00SIZECONCEN" / f"EC{yy}00SIZECONCEN.dat",
                     sep="|", dtype=str, keep_default_na=False)
    df.columns = [c.lstrip("#") for c in df.columns]
    code = f"NAICS{year}"
    label = f"{code}_LABEL" if f"{code}_LABEL" in df else f"{code}_TTL"
    df = df[(df.GEOTYPE == "01") & (df.TYPOP == "00")
            & df[code].str.fullmatch(r"3[1-3]\d{4}")]

    def value(col):
        v = pd.to_numeric(df[col], errors="coerce")
        return v.where(df[f"{col}_F"].isin(["", "0"]))

    df = df.assign(val_pct=value("VAL_PCT"), hhi=value("HHI"), rcptot=value("RCPTOT"),
                   firms=pd.to_numeric(df.FIRM, errors="coerce"))
    by = {c: df[df.CONCENFI == c].set_index(code) for c in ("001", "604", "608", "620", "650")}
    out = pd.DataFrame({
        "label": by["001"][label],
        "firms_census": by["001"]["firms"],
        "shipments": by["001"]["rcptot"] * 1000,
        "cr4": by["604"]["val_pct"],
        "cr8": by["608"]["val_pct"],
        "cr20": by["620"]["val_pct"],
        "hhi": by["650"]["hhi"],
    })
    out.index.name = "naics"
    return out.dropna(subset=["cr8"])


def load_concordance():
    """2017 -> 2022 NAICS, for firms whose Compustat code uses the other vintage."""
    df = pd.read_excel(RAW / "2017_to_2022_NAICS.xlsx", header=None, dtype=str)
    header = df.index[df.apply(lambda r: r.astype(str).str.contains("2017 NAICS Code").any(), axis=1)][0]
    df.columns = df.iloc[header].astype(str).str.strip()
    df = df.iloc[header + 1:]
    return pd.DataFrame({"n17": naics6(df["2017 NAICS Code"]),
                         "n22": naics6(df["2022 NAICS Code"])}).dropna()


def fetch_trade(year, key):
    """US imports and exports by 6-digit NAICS for a calendar year, cached to disk."""
    cache = RAW / f"trade_{year}.csv"
    if cache.exists():
        return pd.read_csv(cache, dtype={"naics": str}).set_index("naics")

    def get(flow, var):
        url = (f"https://api.census.gov/data/timeseries/intltrade/{flow}/naics"
               f"?get=NAICS,{var}&time={year}-12&key={key}")
        with urllib.request.urlopen(url, timeout=180) as r:
            rows = json.load(r)
        df = pd.DataFrame(rows[1:], columns=rows[0])
        df = df[df.NAICS.str.fullmatch(r"3[1-3]\d{4}")]
        return pd.to_numeric(df.set_index("NAICS")[var]).groupby(level=0).sum()

    out = pd.DataFrame({"imports": get("imports", "GEN_VAL_YR"),
                        "exports": get("exports", "ALL_VAL_YR")})
    out.index.name = "naics"
    total = out.imports.sum() / 1e12
    if not 1.0 < total < 4.0:
        raise RuntimeError(f"US manufacturing imports for {year} came to ${total:.2f}T; expected ~$2-3T")
    out.to_csv(cache)
    return out


def load_compustat(path):
    df = read_any(path)
    df.columns = df.columns.str.lower()
    for col, val in [("indfmt", "INDL"), ("datafmt", "STD"), ("popsrc", "D"), ("consol", "C")]:
        if col in df:
            df = df[df[col] == val]
    df["gvkey"] = df.gvkey.astype(str).str.zfill(6)
    df = df.dropna(subset=["fyear"]).astype({"fyear": int})
    df = df.sort_values("datadate").drop_duplicates(["gvkey", "fyear"], keep="last")

    df["naics6"] = naics6(df["naicsh"]) if "naicsh" in df else np.nan
    if "naics" in df:
        df["naics6"] = df.naics6.fillna(naics6(df["naics"]))
    if "loc" in df:
        df = df[df["loc"] == "USA"]  # Bain's firms were US companies filing with the SEC

    for col in ["xrd", "xad", "xsga", "xint"]:
        if col in df:
            df[col] = df[col].fillna(0)

    df = df.sort_values(["gvkey", "fyear"])
    prev = df.groupby("gvkey").shift(1)
    consecutive = prev.fyear == df.fyear - 1
    df["lag_ceq"] = prev.ceq.where(consecutive)
    df["lag_at"] = prev["at"].where(consecutive)

    # Bain's measure: net profit after taxes / net worth at the beginning of the year.
    # Buybacks have pushed many firms' book equity to zero or below, where ROE is meaningless.
    df["roe"] = (df.ni / df.lag_ceq).where(df.lag_ceq > 0) * 100
    df["roa"] = (df.ni / df.lag_at).where(df.lag_at > 0) * 100
    df["oroa"] = (df.oiadp / df.lag_at).where(df.lag_at > 0) * 100
    df["pcm"] = ((df.sale - df.cogs - df.xsga) / df.sale).where(df.sale > 0) * 100
    return df


def load_segments(path):
    """Share of each firm-year's sales in its largest 6-digit NAICS segment."""
    seg = read_any(path)
    seg.columns = seg.columns.str.lower()
    if "stype" in seg:
        # Product-line segments; since SFAS 131 many firms label these operating segments.
        # A firm reports one or the other, so prefer BUSSEG and fall back to OPSEG.
        seg["stype"] = seg.stype.astype(str).str.upper()
        seg = seg[seg.stype.isin(["BUSSEG", "OPSEG"])]
        has_bus = seg.groupby(["gvkey", "datadate"]).stype.transform(lambda s: (s == "BUSSEG").any())
        seg = seg[(seg.stype == "BUSSEG") | ~has_bus]
    seg["gvkey"] = seg.gvkey.astype(str).str.zfill(6)
    seg["datadate"] = pd.to_datetime(seg.datadate)
    seg["srcdate"] = pd.to_datetime(seg.srcdate)
    # Restated segments appear again under later source dates; keep the original filing
    seg = seg[seg.srcdate >= seg.datadate]
    seg = seg[seg.srcdate == seg.groupby(["gvkey", "datadate"]).srcdate.transform("min")]
    seg["naics_seg"] = naics6(seg.naicss1)
    seg = seg[seg.sales > 0]
    by_code = seg.groupby(["gvkey", "datadate", "naics_seg"]).sales.sum().reset_index()
    total = by_code.groupby(["gvkey", "datadate"]).sales.transform("sum")
    by_code["share"] = by_code.sales / total
    top = by_code.sort_values("share").groupby(["gvkey", "datadate"]).tail(1)
    return top[["gvkey", "datadate", "naics_seg", "share"]]


# ---------------------------------------------------------------------------
# Markups: De Loecker, Eeckhout & Unger (2020)
# ---------------------------------------------------------------------------

def add_markups(df):
    """Firm-year markup = theta * sales / COGS, the De Loecker-Eeckhout-Unger formula.

    DEU's headline theta comes from estimating production functions (Ackerberg-Caves-Frazer).
    We don't use that: with COGS as the flexible input it isn't identified (Gandhi, Navarro &
    Rivers 2020). On simulated firms with a true theta of 0.70, it converged to about 0.90-1.0,
    because theta = 1 also satisfies its moment conditions. Instead theta comes from cost shares,
    DEU's robustness method, or is fixed at DEU's average of 0.85.
    """
    d = df.copy()
    ratio = d.sale / d.cogs
    ok = (d.sale > 0) & (d.cogs > 0) & (d.ppegt > 0) & d.naics6.str.match(r"3[1-3]", na=False)
    lo, hi = ratio[ok].quantile([0.01, 0.99])  # DEU trim the sales/COGS ratio at 1% and 99%
    ok &= ratio.between(lo, hi)
    d["sub3"] = d.naics6.str[:3]

    # Cost-share theta: COGS / (COGS + r K), industry-year median (DEU's cost-share approach)
    r = d.fyear.map(lambda y: (FED_FUNDS.get(y, np.nan) - INFLATION.get(y, np.nan)) / 100 + DEPRECIATION)
    share = (d.cogs / (d.cogs + r * d.ppegt)).where(ok)
    theta_cs = share.groupby([d.sub3, d.fyear]).transform("median")
    d["mu_cs"] = (theta_cs * ratio).where(ok)
    d["mu_fixed"] = (THETA_FIXED * ratio).where(ok)

    # Traina (2018): COGS leaves out R&D, marketing and other SG&A, which flatters R&D-heavy
    # industries. Treat COGS + SG&A as the variable input instead, with its own cost share.
    opex = d.cogs + d.xsga
    share_opex = (opex / (opex + r * d.ppegt)).where(ok)
    d["mu_opex"] = (share_opex.groupby([d.sub3, d.fyear]).transform("median") * d.sale / opex).where(ok)
    thetas = theta_cs[ok].groupby([d.sub3[ok], d.fyear[ok]]).first().unstack()
    return d, thetas


# ---------------------------------------------------------------------------
# Building the sample
# ---------------------------------------------------------------------------

def winsorize(s, p=WINSOR):
    lo, hi = s.quantile([p, 1 - p])
    return s.clip(lo, hi)


def build_window(fa, seg, conc, census_year, years, concordance, trade, log):
    w = fa[fa.fyear.isin(years)].copy()
    log(f"firm-years in window, US firms: {len(w):,}")

    if seg is not None:
        w["datadate"] = pd.to_datetime(w.datadate)
        w = w.merge(seg, on=["gvkey", "datadate"], how="left")
        # Bain assigned each firm to the industry it was "primarily occupied" in
        w["naics6"] = w.naics_seg.where(w.share >= PRIMARY_SHARE).fillna(w.naics6)
        diversified = w.share < PRIMARY_SHARE
        log(f"dropped {diversified.sum():,} firm-years with < {PRIMARY_SHARE:.0%} of sales in one industry")
        w = w[~diversified]

    w = w[w.naics6.str.fullmatch(r"3[1-3]\d{4}", na=False)]
    log(f"firm-years in manufacturing (6-digit NAICS 31-33): {len(w):,}")

    if census_year == 2022:
        unmatched = ~w.naics6.isin(conc.index)
        remap = concordance.drop_duplicates("n17").set_index("n17").n22
        w.loc[unmatched, "naics6"] = w.loc[unmatched, "naics6"].map(remap).fillna(w.loc[unmatched, "naics6"])

    w = w[w.naics6.isin(conc.index)]
    log(f"firm-years matched to a Census concentration ratio: {len(w):,}")

    # A firm belongs to the industry it reports most often within the window
    w["naics6"] = w.groupby("gvkey").naics6.transform(lambda s: s.mode().iloc[0])

    firm = w.groupby("gvkey").agg(
        conm=("conm", "last"), naics=("naics6", "first"), n_years=("fyear", "nunique"),
        roe=("roe", "mean"), roa=("roa", "mean"), oroa=("oroa", "mean"),
        pcm=("pcm", "mean"), mu_cs=("mu_cs", "mean"), mu_fixed=("mu_fixed", "mean"), mu_opex=("mu_opex", "mean"),
        net_worth=("lag_ceq", "first"), assets=("at", "mean"), sales=("sale", "mean"),
    )
    firm = firm[firm.n_years >= MIN_YEARS]
    log(f"firms with at least {MIN_YEARS} years of data: {len(firm):,}")
    # Bain's firms were operating businesses; pre-revenue biotech and shells are not
    firm = firm[firm.sales >= MIN_SALES]
    log(f"firms with average sales of at least ${MIN_SALES}M: {len(firm):,}")

    w = w[w.gvkey.isin(firm.index)].assign(margin=lambda d: d.sale - d.cogs - d.xsga)

    def pooled(num, den):
        """Industry-year ratio of sums, using only firm-years where both parts exist."""
        ok = w[num].notna() & (w[den] > 0)
        g = w[ok].groupby(["naics6", "fyear"])
        return g[num].sum() / g[den].sum() * 100

    def sales_weighted(col):
        """DEU aggregate firm markups weighted by sales."""
        ok = w[col].notna() & (w.sale > 0)
        g = w[ok].assign(ws=lambda d: d[col] * d.sale).groupby(["naics6", "fyear"])
        return g.ws.sum() / g.sale.sum()

    yearly = pd.DataFrame({
        "roe": pooled("ni", "lag_ceq"),
        "roa": pooled("ni", "lag_at"),
        "oroa": pooled("oiadp", "lag_at"),
        "pcm": pooled("margin", "sale"),
        "mu_cs": sales_weighted("mu_cs"),
        "mu_fixed": sales_weighted("mu_fixed"),
        "mu_opex": sales_weighted("mu_opex"),
    })
    # Bain: weight firms by size within each year, then a simple average across years
    ind = yearly.groupby(level=0).mean()
    totals = w.groupby("naics6")[["sale", "ppent", "xrd", "xad"]].sum()
    ind["capital_intensity"] = totals.ppent / totals.sale
    ind["rd_intensity"] = totals.xrd / totals.sale
    ind["ad_intensity"] = totals.xad / totals.sale
    ind["n_firms"] = firm.groupby("naics").size()
    ind.index.name = "naics"
    ind = ind.join(conc)

    if trade is not None:
        t = trade.reindex(ind.index)
        domestic = ind.shipments - t.exports
        consumption = domestic + t.imports
        ind["import_share"] = (t.imports / consumption).where(domestic > 0) * 100
        # Top-8 domestic firms' share of US consumption, assuming they export in proportion
        ind["cr8_adj"] = (ind.cr8 * domestic / consumption).where(domestic > 0)

    ind["local_market"] = ind.index.isin(LOCAL_MARKET_NAICS)
    log(f"industries with any profit data: {len(ind)}")
    few = ind.n_firms < MIN_FIRMS
    log(f"dropped {few.sum()} industries with fewer than {MIN_FIRMS} firms")
    log(f"dropped {(ind.local_market & ~few).sum()} local/regional-market industries")
    ind = ind[~few & ~ind.local_market]
    log(f"final sample: {len(ind)} industries")

    firm = firm[firm.naics.isin(ind.index)].join(ind[["cr8", "cr4", "hhi"]], on="naics")
    log(f"final sample: {len(firm)} firms")
    return ind, firm


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def split_test(values, conc, line=BAIN_LINE, weights=None):
    """Bain's dichotomy: mean above vs. below the line, with his large-sample z test."""
    ok = values.notna() & conc.notna()
    v, c = values[ok], conc[ok]
    hi, lo = v[c >= line], v[c < line]
    if weights is None:
        diff = hi.mean() - lo.mean()
        z = diff / np.sqrt(hi.var() / len(hi) + lo.var() / len(lo))
        return dict(n_hi=len(hi), n_lo=len(lo), mean_hi=hi.mean(), mean_lo=lo.mean(),
                    diff=diff, z=z, p=2 * stats.norm.sf(abs(z)))
    w = weights[ok]
    fit = smf.wls("v ~ above", data=pd.DataFrame({"v": v, "above": (c >= line).astype(int)}),
                  weights=w).fit(cov_type="HC1")
    whi = np.average(hi, weights=w[c >= line])
    wlo = np.average(lo, weights=w[c < line])
    return dict(n_hi=len(hi), n_lo=len(lo), mean_hi=whi, mean_lo=wlo, diff=whi - wlo,
                z=fit.tvalues["above"], p=fit.pvalues["above"])


def deciles(ind, col="roe"):
    bins = pd.cut(ind.cr8, bins=np.arange(0, 101, 10), right=False, labels=[f"{i}-{i + 9.9}" for i in range(0, 100, 10)])
    return ind.groupby(bins, observed=False)[col].agg(["size", "mean"]).iloc[::-1]


def threshold_scan(ind, col="roe"):
    rows = []
    for line in range(20, 96):
        above = (ind.cr8 >= line) & ind[col].notna()
        below = (ind.cr8 < line) & ind[col].notna()
        if min(above.sum(), below.sum()) >= 5:
            rows.append(dict(line=line, **split_test(ind[col], ind.cr8, line)))
    return pd.DataFrame(rows)


def size_table(firm, cpi_year):
    """Bain's Table IV: firm profit rates by beginning net worth, above vs. below the line."""
    scale = CPI[cpi_year] / CPI[1936]
    edges_1936 = [0, 0.5e6, 1e6, 5e6, 10e6, 50e6, np.inf]
    edges = [e * scale / 1e6 for e in edges_1936]  # Compustat is in $ millions
    labels = ["< $0.5M", "$0.5-1M", "$1-5M", "$5-10M", "$10-50M", "> $50M"]
    f = firm[firm.net_worth > 0].copy()
    f["roe_w"] = winsorize(f.roe)
    f["size"] = pd.cut(f.net_worth, edges, labels=labels)
    f["group"] = np.where(f.cr8 >= BAIN_LINE, "above 70", "below 70")
    t = f.pivot_table(index="size", columns="group", values="roe_w", aggfunc=["size", "mean"], observed=False)
    t.columns = [f"{a}_{b}".replace("size", "n").replace("mean", "roe") for a, b in t.columns]
    t.index = [f"{lab} in 1936 = ${lo:,.0f}M+ today" if np.isinf(hi) else f"{lab} in 1936 = ${lo:,.0f}-{hi:,.0f}M today"
               for lab, lo, hi in zip(labels, edges[:-1], edges[1:])]
    return t.iloc[::-1]


def demsetz(firm, col="roa"):
    """Demsetz (1973): if concentration enables collusion, small firms should gain too."""
    f = firm.dropna(subset=[col, "cr8", "assets"]).copy()
    f["y"] = winsorize(f[col])
    f["size_q"] = pd.qcut(f.assets, 4, labels=["Q1 smallest", "Q2", "Q3", "Q4 largest"])
    f["cr8_bin"] = pd.cut(f.cr8, [0, 30, 50, 70, 101], right=False,
                          labels=["< 30", "30-50", "50-70", ">= 70"])
    table = f.pivot_table(index="cr8_bin", columns="size_q", values="y", aggfunc="mean", observed=False)
    counts = f.pivot_table(index="cr8_bin", columns="size_q", values="y", aggfunc="size", observed=False)
    f["large"] = (f.size_q == "Q4 largest").astype(int)
    fit = smf.ols("y ~ cr8 * large", data=f).fit(cov_type="cluster", cov_kwds={"groups": f.naics})
    return table, counts, fit


def markup_trend(fa, conc):
    """Sales-weighted manufacturing markup by year, overall and by 2017 concentration."""
    d = fa[fa.mu_cs.notna() & (fa["sale"] >= MIN_SALES)].copy()
    d["high"] = d.naics6.map(conc.cr8) >= BAIN_LINE
    d = d[d.fyear.between(2013, 2025) & d.naics6.isin(conc.index)]

    def weighted(g, col):
        ok = g[col].notna()
        return np.average(g.loc[ok, col], weights=g.loc[ok, "sale"]) if ok.any() else np.nan

    rows = []
    for year, g in d.groupby("fyear"):
        rows.append({"year": year, "firms": len(g),
                     "all, cost share": weighted(g, "mu_cs"), "all, fixed theta": weighted(g, "mu_fixed"), "all, COGS+SG&A": weighted(g, "mu_opex"),
                     "CR8 >= 70": weighted(g[g.high], "mu_cs"), "CR8 < 70": weighted(g[~g.high], "mu_cs")})
    return pd.DataFrame(rows).set_index("year")


def trend_plot(trend, path):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(trend.index, trend["all, cost share"], color="#333333", lw=2, label="All manufacturing (cost share)")
    ax.plot(trend.index, trend["all, fixed theta"], color="#333333", lw=1, ls="--",
            label="All manufacturing (fixed theta = 0.85)")
    ax.plot(trend.index, trend["all, COGS+SG&A"], color="#333333", lw=1, ls=":", label="All manufacturing (COGS + SG&A)")
    ax.plot(trend.index, trend["CR8 >= 70"], color="#c0392b", label="Industries with CR8 >= 70 (cost share)")
    ax.plot(trend.index, trend["CR8 < 70"], color="#2a6fdb", label="Industries with CR8 < 70 (cost share)")
    ax.set_xlabel("Fiscal year")
    ax.set_ylabel("Sales-weighted markup (price / marginal cost)")
    ax.set_title("US manufacturing markups, 2013-2025")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def regressions(ind):
    data = ind.replace([np.inf, -np.inf], np.nan)
    # Entry-barrier proxies in the spirit of Bain (1956): capital requirements, R&D, advertising
    candidates = ["capital_intensity", "rd_intensity", "ad_intensity", "import_share"]
    controls = " + ".join(c for c in candidates
                          if c in data and data[c].notna().sum() > 20 and data[c].std() > 0)
    specs = [
        ("ROE on CR8", "roe ~ cr8", "cr8"),
        ("ROE on CR8 + controls", f"roe ~ cr8 + {controls}", "cr8"),
        ("ROE on above-70 + controls", f"roe ~ above70 + {controls}", "above70"),
        ("ROE on log HHI + controls", f"roe ~ np.log(hhi) + {controls}", "np.log(hhi)"),
        ("ROA on CR8 + controls", f"roa ~ cr8 + {controls}", "cr8"),
        ("Operating ROA on CR8 + controls", f"oroa ~ cr8 + {controls}", "cr8"),
        ("Price-cost margin on CR8 + controls", f"pcm ~ cr8 + {controls}", "cr8"),
        ("Markup (cost share) on CR8 + controls", f"mu_cs ~ cr8 + {controls}", "cr8"),
        ("Markup (cost share) on log HHI + controls", f"mu_cs ~ np.log(hhi) + {controls}", "np.log(hhi)"),
        ("Markup (fixed theta) on CR8 + controls", f"mu_fixed ~ cr8 + {controls}", "cr8"),
        ("Markup (COGS+SG&A) on CR8", "mu_opex ~ cr8", "cr8"),
        ("Markup (COGS+SG&A) on CR8 + controls", f"mu_opex ~ cr8 + {controls}", "cr8"),
    ]
    if "cr8_adj" in data and data.cr8_adj.notna().sum() > 20:
        specs += [("ROE on import-adjusted CR8 + controls", f"roe ~ cr8_adj + {controls}", "cr8_adj"),
                  ("ROA on import-adjusted CR8 + controls", f"roa ~ cr8_adj + {controls}", "cr8_adj")]
    data["above70"] = (data.cr8 >= BAIN_LINE).astype(int)
    rows = []
    for name, formula, term in specs:
        fit = smf.ols(formula, data=data).fit(cov_type="HC1")
        rows.append(dict(spec=name, coef=fit.params[term], se=fit.bse[term], p=fit.pvalues[term],
                         n=int(fit.nobs), r2=fit.rsquared))
    return pd.DataFrame(rows), controls


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def fmt_split(name, r, unit="%"):
    digits = 1 if unit == "%" else 3
    return (f"| {name} | {r['n_hi']} / {r['n_lo']} | {r['mean_hi']:.{digits}f}{unit} | {r['mean_lo']:.{digits}f}{unit} | "
            f"{r['diff']:+.{digits}f} | {r['z']:.2f} | {r['p']:.3f} |")


def scatter(ind, window, path):
    fig, ax = plt.subplots(figsize=(8, 5.5))
    bx, by = zip(*BAIN_TABLE_I)
    ax.scatter(bx, by, marker="x", color="#999999", label="Bain 1951 (1936-40)", zorder=2)
    ax.scatter(ind.cr8, ind.roe.clip(-30, 60), color="#2a6fdb", alpha=0.7,
               label=f"Modern (window {window})", zorder=3)
    ax.axvline(BAIN_LINE, color="#c0392b", ls="--", lw=1)
    for (lo, hi), color in [((0, 70), "#2a6fdb"), ((70, 101), "#2a6fdb")]:
        m = ind.roe[(ind.cr8 >= lo) & (ind.cr8 < hi)].mean()
        ax.hlines(m, lo, min(hi, 100), color=color, lw=2, alpha=0.5)
    ax.set_xlabel("8-firm concentration ratio (%)")
    ax.set_ylabel("Industry average return on equity (%)")
    ax.set_title(f"Profit rate vs. concentration: Bain's sample and window {window}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def scan_plot(scans, path):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for window, s in scans.items():
        ax.plot(s.line, s.z, label=f"Window {window}")
    ax.axhline(1.96, color="#999999", ls=":", lw=1)
    ax.axhline(-1.96, color="#999999", ls=":", lw=1)
    ax.axvline(BAIN_LINE, color="#c0392b", ls="--", lw=1, label="Bain's 70% line")
    ax.set_xlabel("Cutoff for 'high concentration' (CR8, %)")
    ax.set_ylabel("z-statistic, ROE above vs. below cutoff")
    ax.set_title("Is there still a threshold?")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--compustat", required=True)
    ap.add_argument("--segments")
    ap.add_argument("--census-key-file")
    ap.add_argument("--windows", default="AB")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report = ["# Bain (1951) on modern data: results\n"]
    log_lines = []

    def log(msg):
        print(msg)
        log_lines.append(f"- {msg}")

    fa, thetas = add_markups(load_compustat(args.compustat))
    thetas.to_csv(out / "cost_share_thetas.csv")
    seg = load_segments(args.segments) if args.segments else None
    concordance = load_concordance()
    key = Path(args.census_key_file).read_text().strip() if args.census_key_file else None

    trend = markup_trend(fa, load_concentration(2017))
    trend.to_csv(out / "markup_trend.csv")
    trend_plot(trend, out / "markup_trend.png")
    report.append("## Markup trend, US manufacturing (sales-weighted)\n")
    report.append("Industries split by 2017 concentration. Markup = theta x sales / COGS (De Loecker, "
                  "Eeckhout & Unger 2020).\n")
    report.append(trend.round(3).to_markdown())
    report.append("\n![markup trend](markup_trend.png)\n")
    report.append("Cost-share theta (median COGS / (COGS + rK)) by 3-digit subsector and year:\n")
    report.append(thetas.round(3).to_markdown())
    report.append("")

    scans = {}
    for window in args.windows:
        cfg = WINDOWS[window]
        y0, y1 = cfg["years"][0], cfg["years"][-1]
        log_lines.append(f"\n**Window {window}: {cfg['census']} concentration, FY{y0}-{y1}**\n")
        print(f"\n== Window {window}")
        conc = load_concentration(cfg["census"])
        trade = fetch_trade(cfg["census"], key) if key else None
        ind, firm = build_window(fa, seg, conc, cfg["census"], cfg["years"], concordance, trade, log)
        ind.to_csv(out / f"industries_{window}.csv")
        firm.to_csv(out / f"firms_{window}.csv")

        r = report
        r.append(f"\n## Window {window}: {cfg['census']} concentration, FY{y0}–{y1}\n")
        r.append(f"{len(ind)} industries, {len(firm)} firms.\n")

        r.append("### Bain's test: above vs. below 70% (CR8)\n")
        r.append("| Measure | n (above / below) | Above 70 | Below 70 | Difference | z | p |")
        r.append("|---|---|---|---|---|---|---|")
        r.append("| *Bain 1951, industry ROE* | *22 / 20* | *12.1%* | *6.9%* | *+5.2* | | *< 0.001* |")
        r.append(fmt_split("Industry ROE (Bain's method)", split_test(ind.roe, ind.cr8)))
        r.append(fmt_split("Industry ROA", split_test(ind.roa, ind.cr8)))
        r.append(fmt_split("Industry operating ROA", split_test(ind.oroa, ind.cr8)))
        r.append(fmt_split("Industry price-cost margin", split_test(ind.pcm, ind.cr8)))
        if "cr8_adj" in ind:
            r.append(fmt_split("Industry ROE, import-adjusted CR8", split_test(ind.roe, ind.cr8_adj)))
        r.append(fmt_split("Firm ROE, unweighted (raw)", split_test(firm.roe, firm.cr8)))
        r.append(fmt_split("Firm ROE, unweighted (winsorized)", split_test(winsorize(firm.roe), firm.cr8)))
        pos = firm[firm.net_worth > 0]
        r.append(fmt_split("Firm ROE, weighted by net worth", split_test(winsorize(pos.roe), pos.cr8, weights=pos.net_worth)))
        r.append("")

        r.append("### Table II analogue: industry ROE by concentration decile\n")
        r.append(deciles(ind).rename(columns={"size": "industries", "mean": "avg ROE (%)"}).round(1).to_markdown())
        r.append("")

        scans[window] = threshold_scan(ind)
        best = scans[window].loc[scans[window].z.abs().idxmax()]
        r.append(f"**Threshold scan:** the strongest split is at CR8 = {best.line:.0f}% "
                 f"(z = {best.z:.2f}, difference {best['diff']:+.1f} points).\n")

        r.append("### Table IV analogue: firm ROE by size (Bain's classes in today's dollars)\n")
        r.append(size_table(firm, 2015 if window == "A" else 2021).round(1).to_markdown())
        r.append("")

        table, counts, fit = demsetz(firm)
        r.append("### Demsetz test: firm ROA by concentration and firm size (asset quartiles)\n")
        r.append(table.round(1).to_markdown())
        r.append("\nFirms per cell:\n")
        r.append(counts.to_markdown())
        r.append(f"\nRegression `ROA ~ CR8 × Large` (clustered by industry): "
                 f"CR8 slope for smaller firms = {fit.params['cr8']:.3f} (p = {fit.pvalues['cr8']:.3f}); "
                 f"extra slope for the largest quartile = {fit.params['cr8:large']:.3f} "
                 f"(p = {fit.pvalues['cr8:large']:.3f}).\n")
        r.append("Collusion predicts a positive slope for small firms too. Efficiency predicts a flat slope for "
                 "small firms and a positive extra slope for large ones.\n")

        r.append("### Markups instead of profits\n")
        r.append("| Measure | n (above / below) | Above 70 | Below 70 | Difference | z | p |")
        r.append("|---|---|---|---|---|---|---|")
        r.append(fmt_split("Industry markup, cost share", split_test(ind.mu_cs, ind.cr8), unit=""))
        r.append(fmt_split("Industry markup, fixed theta", split_test(ind.mu_fixed, ind.cr8), unit=""))
        r.append(fmt_split("Industry markup, COGS + SG&A (Traina)", split_test(ind.mu_opex, ind.cr8), unit=""))
        r.append(fmt_split("Firm markup, COGS + SG&A (winsorized)", split_test(winsorize(firm.mu_opex), firm.cr8), unit=""))
        r.append(fmt_split("Firm markup, cost share (winsorized)", split_test(winsorize(firm.mu_cs), firm.cr8), unit=""))
        r.append(fmt_split("Firm markup, cost share, weighted by sales",
                           split_test(winsorize(firm.mu_cs), firm.cr8, weights=firm.sales), unit=""))
        r.append("")
        mscan = threshold_scan(ind, "mu_cs")
        mbest = mscan.loc[mscan.z.abs().idxmax()]
        r.append(f"**Threshold scan (cost-share markup):** strongest split at CR8 = {mbest.line:.0f}% "
                 f"(z = {mbest.z:.2f}, difference {mbest['diff']:+.3f}).\n")
        mtable, mcounts, mfit = demsetz(firm, "mu_cs")
        r.append("**Demsetz test with markups** (cost share, by concentration and asset quartile):\n")
        r.append(mtable.round(3).to_markdown())
        r.append(f"\nCR8 slope for smaller firms = {mfit.params['cr8']:.4f} (p = {mfit.pvalues['cr8']:.3f}); "
                 f"extra slope for the largest quartile = {mfit.params['cr8:large']:.4f} "
                 f"(p = {mfit.pvalues['cr8:large']:.3f}).\n")

        reg, controls = regressions(ind)
        r.append("### Regressions (industry level, robust SEs)\n")
        r.append(f"Controls: {controls.replace(' + ', ', ')}.\n")
        r.append(reg.round(4).to_markdown(index=False))
        r.append("")

        r.append("### Table I analogue: industries by concentration\n")
        cols = ["label", "cr8", "roe", "roa", "n_firms"] + (["import_share", "cr8_adj"] if "cr8_adj" in ind else [])
        r.append(ind.sort_values("cr8", ascending=False)[cols].round(1).to_markdown())
        r.append("")

        scatter(ind, window, out / f"scatter_{window}.png")
        r.append(f"![scatter](scatter_{window}.png)\n")

    scan_plot(scans, out / "threshold_scan.png")
    report.append("\n## Threshold scan\n\n![scan](threshold_scan.png)\n")
    report.append("\n## Sample construction log\n")
    report.extend(log_lines)
    (out / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(f"\nWrote {out / 'REPORT.md'}")


if __name__ == "__main__":
    main()
