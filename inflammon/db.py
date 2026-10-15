"""DuckDB storage for aggregated public surveillance extracts.

The file holds counts and metadata, not raw FAERS case narratives.
Rebuild it with ``make refresh``. The dashboard reads the JSON snapshot,
not this file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import duckdb

DEFAULT_PATH = Path("data/inflammon.duckdb")

SCHEMA = """
CREATE TABLE IF NOT EXISTS source_runs (
    source VARCHAR,
    status VARCHAR,
    detail VARCHAR,
    rows INTEGER,
    pulled_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS faers_context (
    database_n INTEGER,
    last_updated VARCHAR
);

CREATE TABLE IF NOT EXISTS faers_exposure (
    scope VARCHAR,
    key VARCHAR,
    label VARCHAR,
    drug_class VARCHAR,
    report_count INTEGER
);

CREATE TABLE IF NOT EXISTS faers_pairs (
    scope VARCHAR,
    key VARCHAR,
    drug_class VARCHAR,
    reaction VARCHAR,
    pair_count INTEGER,
    preset BOOLEAN
);

CREATE TABLE IF NOT EXISTS faers_reaction_totals (
    reaction VARCHAR,
    report_count INTEGER
);

CREATE TABLE IF NOT EXISTS faers_quarterly (
    drug_class VARCHAR,
    year INTEGER,
    quarter INTEGER,
    report_count INTEGER
);

CREATE TABLE IF NOT EXISTS recalls (
    recall_number VARCHAR,
    product_description VARCHAR,
    reason VARCHAR,
    status VARCHAR,
    classification VARCHAR,
    recalling_firm VARCHAR,
    report_date VARCHAR,
    matched_term VARCHAR,
    drug_class VARCHAR
);

CREATE TABLE IF NOT EXISTS alerts (
    source VARCHAR,
    title VARCHAR,
    link VARCHAR,
    published VARCHAR,
    summary VARCHAR,
    tags VARCHAR
);

CREATE TABLE IF NOT EXISTS publication_counts (
    topic VARCHAR,
    label VARCHAR,
    topic_type VARCHAR,
    grain VARCHAR,
    period VARCHAR,
    period_start VARCHAR,
    count INTEGER,
    partial BOOLEAN
);

CREATE TABLE IF NOT EXISTS trial_counts (
    topic VARCHAR,
    label VARCHAR,
    grain VARCHAR,
    period VARCHAR,
    period_start VARCHAR,
    count INTEGER,
    partial BOOLEAN
);

CREATE TABLE IF NOT EXISTS trial_recent (
    nct_id VARCHAR,
    title VARCHAR,
    status VARCHAR,
    phase VARCHAR,
    conditions VARCHAR,
    start_date VARCHAR,
    last_update VARCHAR,
    topic VARCHAR
);

CREATE TABLE IF NOT EXISTS publication_recent (
    pmid VARCHAR,
    title VARCHAR,
    journal VARCHAR,
    published VARCHAR,
    topic VARCHAR,
    link VARCHAR
);

CREATE TABLE IF NOT EXISTS cdc_arthritis (
    year VARCHAR,
    question VARCHAR,
    data_value DOUBLE,
    unit VARCHAR,
    stratification VARCHAR,
    low_ci DOUBLE,
    high_ci DOUBLE
);
"""

TABLES = [
    "source_runs",
    "faers_context",
    "faers_exposure",
    "faers_pairs",
    "faers_reaction_totals",
    "faers_quarterly",
    "recalls",
    "alerts",
    "publication_counts",
    "trial_counts",
    "trial_recent",
    "publication_recent",
    "cdc_arthritis",
]


def connect(path: Path = DEFAULT_PATH) -> duckdb.DuckDBPyConnection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(path))
    connection.execute(SCHEMA)
    return connection


def reset(connection: duckdb.DuckDBPyConnection) -> None:
    for table in TABLES:
        connection.execute(f"DELETE FROM {table}")


def insert_rows(
    connection: duckdb.DuckDBPyConnection,
    table: str,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any]],
) -> None:
    if not rows:
        return
    placeholders = ", ".join(["?"] * len(columns))
    column_list = ", ".join(columns)
    connection.executemany(
        f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})",
        [tuple(row) for row in rows],
    )
