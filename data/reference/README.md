# Reference data (synthetic)

All institutions and code lists here are **synthetic**. The LCR line codes are a simplified teaching template, not the official regulatory template.

In the target design these live in the reference-data hub (PostgreSQL, versioned and bitemporal) and are published as Iceberg tables. In the POC they are loaded into `lakehouse.reference.*` by `pipelines/spark/load_reference.py`.
