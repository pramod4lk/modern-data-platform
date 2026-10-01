# Superset dashboards

Dashboards are built in the Superset UI, then **exported and committed here** so they are versioned like code.

## Connect Superset to Trino
Settings → Database connections → + Database → Trino:
```
trino://superset@trino.lakehouse.svc.cluster.local:8080/iceberg
```

## First dashboard: "LCR monitoring (synthetic)"
Dataset: `iceberg.gold.gold_lcr_by_institution`

| Chart | Type | Metric / dimension |
| --- | --- | --- |
| LCR by institution | Bar | `lcr_ratio` by `institution_id`, reference line at 1.0 |
| LCR trend | Line | `avg(lcr_ratio)` by `reporting_period`, split by `peer_group` |
| Institutions below 120% | Table | filter `lcr_ratio < 1.2` |
| Data quality | Table | `iceberg.ops.dq_results`, failures by `rule_id` and `submission_id` |

## Export / import
```bash
# export (from the Superset pod)
superset export-dashboards -f /tmp/dashboards.zip
kubectl cp bi/<superset-pod>:/tmp/dashboards.zip ./dashboards.zip
unzip dashboards.zip -d data/dashboards/superset/
```
Import with `superset import-dashboards -p <zip>`.
