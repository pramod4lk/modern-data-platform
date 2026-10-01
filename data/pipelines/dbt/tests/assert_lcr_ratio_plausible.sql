-- Rule LCR-101 (warning): LCR between 50% and 1000%. Returns implausible rows.
{{ config(severity='warn') }}
select institution_id, reporting_period, lcr_ratio
from {{ ref('gold_lcr_by_institution') }}
where lcr_ratio not between 0.5 and 10
