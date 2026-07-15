# Module 1 – Data Acquisition

## Overview

The **Data Acquisition** module continuously collects financial data from heterogeneous sources, normalizes it into a canonical schema, validates integrity, and streams it to downstream processing. It focuses strictly on data reliability and traceability without performing financial analysis.


## Core Objectives & Responsibilities

* **Ingestion:** Supports both batch historical backfill and near real-time continuous ingestion.
* **Processing:** Standardizes source formats, strips HTML/formatting noise, and executes duplicate detection.
* **Storage & Transmission:** Persists immutable raw data for auditing/replay and publishes validated events asynchronously.


## Input Sources

| Source Category | Purpose | Key Examples |
| --- | --- | --- |
| **Market Data** | Quantitative inputs for prediction | OHLCV, volume, market indices, stats |
| **Financial News** | Textual core for Knowledge Graph | Company, industry, macro-economic news |
| **Social Posts** | Market sentiment estimation (noisy) | FireAnt posts, investment forums |
| **Corporate Info** | Long-term background knowledge | Financial statements, annual reports, disclosures |
| **Macroeconomic Data** | Broad external economic context | Interest rates, inflation, CPI, commodity prices |


## System Outputs

1. **Raw Document Storage (MongoDB):** Immutable archive of original documents used for debugging, auditing, and pipeline replays.
2. **Processing Event Stream (Apache Kafka):** Normalized, validated documents published asynchronously for downstream NLP consumption.


## Canonical Document Schema

All text documents are converted into a unified structure to abstract source implementation details:

* `id` / `title` / `content`
* `published_at` / `retrieved_at`
* `source` / `author` / `url` / `language`
* `document_type` / `symbols` (ticker tags)
* `raw_html` / `metadata`



## Document Lifecycle

```text
DISCOVERED ──> FETCHED ──> VALIDATED ──> NORMALIZED ──> DEDUPLICATED ──> STORED ──> PUBLISHED

```

* **DISCOVERED / FETCHED:** URL identified and raw content downloaded.
* **VALIDATED / NORMALIZED:** Schema compliance verified; text mapped to the canonical structure.
* **DEDUPLICATED:** Near and exact duplicate detection executed.
* **STORED / PUBLISHED:** Immutable raw copy written to MongoDB; standard event emitted to Kafka.

