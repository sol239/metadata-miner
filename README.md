# Metadata Miner

The aim of the Metadata Miner is to automatically extract, derive, and infer technical, structural, statistical, and business metadata from database management systems (DBMS).

| Metadata Type | Description | Examples | Extraction Method |
|---|---|---|---|
| **Technical Metadata** | Describes the technical properties and definitions of database objects. | Schemas, tables, columns, data types, constraints, indexes, views, sequences. | System catalogs |
| **Structural Metadata** | Describes the organization, relationships, and dependencies between database objects. | Primary keys, foreign keys, table relationships, view dependencies, object hierarchies. | System catalogs, SQL analysis, inference |
| **Statistical Metadata** | Describes the statistical characteristics and distributions of stored data. | Row counts, distinct counts, NULL ratios, min/max values, value distributions, histograms. | System statistics, SQL profiling |
| **Business Metadata** | Describes the business meaning, purpose, and rules associated with data. | Business definitions, entity descriptions, business domains, semantic classifications, business rules. | Database comments, documentation, LLM inference, human validation |

## Metadata Acquisition Methods

| Method | Description | Examples |
|---|---|---|
| **Extracted** | Metadata retrieved directly from the DBMS. | Column names, data types, constraints, indexes, declared relationships. |
| **Derived** | Metadata calculated from existing data or metadata. | NULL ratios, distinct counts, duplicate counts, inferred key candidates. |
| **Inferred** | Metadata estimated using heuristics or LLMs. | Business descriptions, implicit relationships, semantic classifications, potential business rules. |

Inferred metadata should include its source, confidence level where meaningful, and validation status to distinguish hypotheses from verified facts.