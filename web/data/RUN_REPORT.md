# Ingestion report

Generated 2026-10-15T06:37:57+00:00.
openFDA extract last updated 2026-07-30.
FAERS reports in the extract: 20692690.

## Sources

- **openFDA drug/event** — ok. openFDA drug/event last_updated=2026-07-30; database_n=20692690
- **openFDA drug/enforcement** — ok. 156 recalls across 50 product searches
- **FDA MedWatch, Drugs RSS, and Drug Safety Communications** — ok. FDA MedWatch RSS 20 items; FDA Drugs RSS 20 items; DSC RSS unavailable (HTTP 404); DSC HTML index 43 links
- **ClinicalTrials.gov API v2** — ok. 135 trial counts, 40 recent studies, 0 failed queries
- **PubMed E-utilities** — ok. 190 publication counts, 24 recent citations, 0 failed queries
- **CDC Chronic Disease Indicators hksd-2xuw** — ok. 7 US overall arthritis indicator rows. A data.cdc.gov catalog search for inflammatory bowel disease did not return a surveillance table comparable to Chronic Disease Indicators. IBD trends on this dashboard use ClinicalTrials.gov and PubMed.

## Known-signal sanity check

A known signal is recovered when the prespecified 2×2 table has at least 3 reports in cell a and either an Evans signal (PRR ≥ 2 and χ² ≥ 4) or a ROR whose 95% lower bound is above 1. JAK thrombosis and MACE are compared with TNF inhibitors. TNF–tuberculosis and NSAID–gastrointestinal bleeding are compared with the rest of the openFDA FAERS extract.

- Pulmonary embolism, JAK inhibitors versus TNF inhibitors: recovered. a=1732, PRR=2.308076 (2.182908–2.44042), ROR=2.316652 (2.190351–2.450236).
- Deep vein thrombosis, JAK inhibitors versus TNF inhibitors: recovered. a=1145, PRR=2.547272 (2.375851–2.731061), ROR=2.553964 (2.381511–2.738904).
- Thrombosis, JAK inhibitors versus TNF inhibitors: recovered. a=1941, PRR=2.239454 (2.125081–2.359983), ROR=2.248568 (2.133037–2.370357).
- Myocardial infarction, JAK inhibitors versus TNF inhibitors: recovered. a=1692, PRR=1.238281 (1.174996–1.304974), ROR=1.239807 (1.176063–1.307006).
- Cerebrovascular accident, JAK inhibitors versus TNF inhibitors: recovered. a=1948, PRR=1.576626 (1.499637–1.657567), ROR=1.580881 (1.503174–1.662606).
- Tuberculosis, TNF inhibitors versus all other FAERS reports: recovered. a=4708, PRR=7.54179 (7.275316–7.818025), ROR=7.562393 (7.294631–7.839985).
- Pulmonary tuberculosis, TNF inhibitors versus all other FAERS reports: recovered. a=1472, PRR=6.88615 (6.463551–7.33638), ROR=6.891934 (6.468697–7.342862).
- Gastrointestinal haemorrhage, NSAIDs versus all other FAERS reports: recovered. a=5507, PRR=2.523204 (2.455482–2.592795), ROR=2.538145 (2.469389–2.608816).
- Gastric ulcer, NSAIDs versus all other FAERS reports: recovered. a=2831, PRR=6.29842 (6.052154–6.554706), ROR=6.32501 (6.076643–6.583528).
- Melaena, NSAIDs versus all other FAERS reports: recovered. a=2322, PRR=4.237757 (4.059586–4.423748), ROR=4.251072 (4.071681–4.438367).

Recovered 10 of 10 prespecified checks.

Counts are ingredient mentions in the openFDA FAERS extract. They are not primary-suspect-only counts and they are not incidence.
