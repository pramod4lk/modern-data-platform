# Secrets

**No secret values are ever committed to this repository.** For the POC, create Secrets by hand with `kubectl`. Later, switch to **Sealed Secrets** or **SOPS + age** so encrypted secrets can live in Git.

Generate strong values, e.g. `openssl rand -base64 24`.

| Secret | Namespace(s) | Keys | Used by |
| --- | --- | --- | --- |
| `pg-polaris`, `pg-keycloak`, `pg-airflow`, `pg-superset`, `pg-openmetadata`, `pg-ledger` | data-system | `username`, `password` (type `kubernetes.io/basic-auth`) | CloudNativePG roles |
| `pg-keycloak` (copy) | identity | `password` | Keycloak DB |
| `keycloak-admin` | identity | `username`, `password` | Keycloak bootstrap admin |
| `polaris-db` | data-system | `username`, `password`, `jdbcUrl` | Polaris |
| `polaris-engine` | lakehouse, streaming, orchestration | `POLARIS_CLIENT_ID`, `POLARIS_CLIENT_SECRET` | Trino, Spark, Flink |
| `s3-credentials` | lakehouse, streaming, orchestration | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Trino, Spark, Flink, Airflow |
| `airflow-metadata` | orchestration | `connection` (`postgresql://airflow:<pw>@pg-rw.data-system.svc.cluster.local:5432/airflow`) | Airflow |
| `openmetadata-db` | governance | `password` | OpenMetadata |
| `grafana-admin` | monitoring | `admin-user`, `admin-password` | Grafana |

## Examples

```bash
# PostgreSQL role secret (repeat per service)
kubectl -n data-system create secret generic pg-airflow \
  --type=kubernetes.io/basic-auth \
  --from-literal=username=airflow --from-literal=password="$(openssl rand -base64 24)"

# S3 credentials (from: radosgw-admin user info --uid=poc)
for ns in lakehouse streaming orchestration; do
  kubectl -n $ns create secret generic s3-credentials \
    --from-literal=AWS_ACCESS_KEY_ID=<access_key> \
    --from-literal=AWS_SECRET_ACCESS_KEY=<secret_key>
done
```

Create namespaces first: `kubectl apply -f platform/namespaces/namespaces.yaml`.
