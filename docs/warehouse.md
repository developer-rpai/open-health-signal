# FAERS warehouse design

This is a design note. The warehouse is not built. The weekly dashboard still reads the openFDA count API and the committed JSON snapshot.

## Store

Quarterly FAERS extracts land as Parquet on Cloudflare R2. GitHub Actions reads them with an ephemeral DuckDB process: download the partitions the watermark names, query, discard the database. Nothing about the case-level extract is committed to the site, and DuckDB does not stay running between jobs.

Object layout:

```text
r2://<bucket>/faers/parquet/
  case/year=YYYY/quarter=Q/
  drug/year=YYYY/quarter=Q/
  reaction/year=YYYY/quarter=Q/
  outcome/year=YYYY/quarter=Q/
  indication/year=YYYY/quarter=Q/
  therapy/year=YYYY/quarter=Q/
  _watermarks/faers.json
```

## Tables

| Table | Grain | Columns to keep |
| --- | --- | --- |
| `case` | one row per case version | `caseid`, `caseversion`, `primaryid`, `receivedate`, `age`, `age_cod`, `sex`, `reporter_country`, `occr_country` |
| `drug` | one drug mention | `primaryid`, `drug_seq`, `role_cod` (suspect, concomitant, interacting), `drugname`, RxNorm ingredient identifier when the name maps |
| `reaction` | one MedDRA preferred term | `primaryid`, `pt` |
| `outcome` | one outcome | `primaryid`, `outc_cod` |
| `indication` | one indication | `primaryid`, `indi_drug_seq`, `indi_pt` |
| `therapy` | one therapy span | `primaryid`, `dsg_drug_seq`, `start_dt`, `end_dt` |

`role_cod` stays on `drug`. The current openFDA counts cannot bind `drugcharacterization = 1` to the same drug element, which is why the live dashboard counts ingredient mentions. The warehouse can restrict PRR and ROR to suspect drugs (`role_cod = 'PS'`) and keep the mention-level figure beside it.

## Dedup

FAERS republishes a case when a follow-up arrives. Keep the latest `caseversion` for each `caseid`, and drop every other version of that case from the quarter being scored. Join drug, reaction, outcome, indication, and therapy through `primaryid` of the surviving version only. A case that moves to a later quarter replaces the older version; the watermark record notes which `primaryid` values were retired.

## Loads

Loads are quarterly and incremental.

1. Read `_watermarks/faers.json`: last completed year and quarter, and the set of `caseid` values already stored.
2. Pull the next FAERS quarterly ASCII files from the public FDA download. Do not re-pull a quarter whose hash matches the watermark.
3. Convert that quarter to Parquet and write the six partitions.
4. Apply the latest-version dedup against prior partitions that share a `caseid`.
5. Write the new watermark only after the Parquet write succeeds.

A failed quarter leaves the previous watermark in place, so the next run retries the same quarter.

## Scores

On each quarterly load, DuckDB computes three disproportionality measures for the prespecified drug–reaction pairs, and for any pair that clears a minimum count:

- **PRR** and **ROR**, with the same 95% intervals, chi-square, and Haldane–Anscombe correction the dashboard uses now.
- **EBGM** (empirical Bayes geometric mean) from a shrinkage model on the same 2×2 table, reported with the fifth percentile of the posterior (`EB05`). A signal screen for the warehouse is EB05 &gt; 2, alongside the Evans rule the site already publishes. The two screens are stored separately so a reader can see where they disagree.

Suspect-only and mention-level ratios are both stored. The published site keeps showing mention-level PRR and ROR until a later phase switches the snapshot over. This document does not change that snapshot.

## Validation

Each quarterly score is checked against two published reference sets:

- **OMOP reference set** of drug–outcome pairs labeled as positive or negative controls.
- **EU-ADR reference set** of the same kind.

Report sensitivity and specificity of the Evans rule, of the ROR lower bound, and of EB05 &gt; 2, on the pairs those sets cover and that the extract actually contains. A missing pair is counted as not evaluated, not as a true negative. The note that ships with the score names the reference-set version and the quarter of FAERS it was run on.

## MedDRA

Reaction and indication strings in FAERS are MedDRA preferred terms. MedDRA is a licensed terminology. This project may redistribute the preferred-term strings that already appear inside a public FAERS record, because those strings are part of the public case extract. It does not redistribute the MedDRA hierarchy, the full preferred-term list, or the SOC/HLGT/HLT maps.

Before any warehouse export is published, verify the current MedDRA redistribution terms against the MSSO license that applies that quarter, and record the answer in the watermark file. If the terms do not allow even the preferred-term strings from the public extract, store MedDRA codes only and drop the strings from the published Parquet.
