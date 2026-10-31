# Data to get

The Census data is already in `data/raw/`. Compustat data is licensed through WRDS and isn't included, so you
need to pull two extracts yourself and save them in `data/compustat/`. A free Census API key is optional.

The analysis reads CSV (plain or zipped), Parquet, SAS or Stata files.

---

## 1. Compustat Fundamentals Annual (required)

This supplies firm profits, the modern version of Bain's SEC data. Save as
`data/compustat/funda_2013_2026.csv.zip`.

### Option A: WRDS web query

1. WRDS → **Get Data** → **Compustat - Capital IQ** → **Compustat** → **North America - Daily** → **Fundamentals Annual**
2. **Date range:** data date from January 2013 through the present. The 2013–14 years supply beginning-of-year
   equity, like Bain's beginning-of-year net worth.
3. **Company codes:** "Search the entire database"
4. **Screening variables:** Consolidation = C, Industry Format = INDL only (untick FS), Data Format = STD,
   Currency = USD and CAD, Company Status = Active and Inactive
5. **Variables:**

| Group | Variables |
|---|---|
| Identifiers | `gvkey fyear conm tic cusip cik fic loc` |
| Industry codes | `naicsh sich naics sic` |
| Income statement | `sale cogs xsga xrd xad ni ib oiadp oibdp txt xint dp` |
| Balance sheet | `ceq seq at lt ppent ppegt` |
| Other | `emp csho prcc_f` |

6. **Output:** comma-delimited, zip compression

### Option B: SQL (WRDS Cloud / Python `wrds` package)

```sql
SELECT f.gvkey, f.datadate, f.fyear, f.conm, f.tic, f.cusip, f.cik, f.fic, f.loc, f.curcd,
       f.naicsh, f.sich, c.naics, c.sic,
       f.sale, f.cogs, f.xsga, f.xrd, f.xad, f.ni, f.ib, f.oiadp, f.oibdp, f.txt, f.xint, f.dp,
       f.ceq, f.seq, f.at, f.lt, f.ppent, f.ppegt, f.emp, f.csho, f.prcc_f
FROM comp.funda f
JOIN comp.company c ON f.gvkey = c.gvkey
WHERE f.indfmt = 'INDL' AND f.datafmt = 'STD' AND f.popsrc = 'D' AND f.consol = 'C'
  AND f.fyear BETWEEN 2013 AND 2025
```

Don't filter to manufacturing yourself. The script does that, because industry codes are sometimes missing in one
field but present in another.

---

## 2. Compustat Historical Segments (strongly recommended)

Bain dropped firms that didn't earn "a substantial majority" of their profits in one industry. Segment data lets
us apply the same rule. Without it, conglomerates get assigned to whichever industry is their primary code. Save as
`data/compustat/segments_hist_2014_2026.csv.zip`.

Use **Historical Segments**, not the regular Segments table: the regular one only goes back about seven years,
which doesn't cover the FY2015–19 window.

- Web: **Compustat - Capital IQ** → **Compustat** → **Historical Segments - Daily** → **Historical Segments**
- Date range 2014–2026, all source years, search the entire database
- Segment types: **Business** and **Operating**. Many firms report product lines as operating segments.
- Variables: `gvkey srcdate stype sid snms sales ops ias naicss1 sics1`

SQL version (the table name may differ slightly on your WRDS):

```sql
SELECT gvkey, datadate, srcdate, stype, sid, snms, sales, ops, ias, naicss1, sics1
FROM comp_segments_hist_daily.wrds_segmerged
WHERE stype IN ('BUSSEG', 'OPSEG') AND datadate BETWEEN '2014-01-01' AND '2026-12-31'
```

---

## 3. Census API key (optional, for the import adjustment)

Free: sign up at <https://api.census.gov/data/key_signup.html>. Save the key in a text file outside the repo and
pass it with `--census-key-file`. Without it, everything except the import-adjusted concentration ratios runs.

---

## Already included

- 2017 and 2022 Economic Census concentration ratios (CR4, CR8, CR20, CR50, HHI) for all manufacturing industries
- Census 2017↔2022 NAICS concordance
