# ADR-0002: Apache Polaris as the Iceberg REST catalog

- **Status:** Proposed (to confirm after M2)
- **Date:** 2026-10-01

## Context
Engines need a shared catalog that tracks the current metadata of each Iceberg table, enforces namespace access and vends scoped storage credentials.

## Options considered
1. **Apache Polaris** (incubating) — Iceberg REST, credential vending, broad industry backing.
2. **Project Nessie** — Iceberg REST plus Git-like branching of the whole catalog.
3. **Hive Metastore** — mature but legacy; ties the design to Hive.

## Decision
Use Polaris in the POC. Because both Polaris and Nessie implement the Iceberg REST API, the choice remains reversible.

## Consequences
- Engines are configured against a REST endpoint, not a metastore.
- Re-evaluate Nessie if catalog-level branching (e.g. month-end reprocessing branches) proves valuable.
