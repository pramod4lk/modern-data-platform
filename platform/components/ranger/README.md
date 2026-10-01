# Apache Ranger (stretch goal, Milestone 5)

Ranger has no official Helm chart. Options for the POC:

1. **Ranger admin + Trino plugin** using community container images (Ranger admin needs PostgreSQL and Solr/OpenSearch for audit). Highest fidelity to the target design; heaviest on memory.
2. **Open Policy Agent (OPA) with Trino's built-in OPA access control.** Much lighter; good for demonstrating row filters and column masks as policy-as-code.
3. **Trino file-based access control** with row filters and column masks. Lightest; proves the concept but is not central policy.

Recommended order for the POC: start with option 3 to prove masking/row filtering, then try option 2. Attempt option 1 only if memory allows.

Target policy to demonstrate:
- `analyst` role sees `gold.*` but `institution_name` masked.
- `supervisor` role sees only rows for institutions in their portfolio.
