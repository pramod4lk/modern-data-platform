-- Fails if Silver contains more than one version for the same institution, period and line.
select institution_id, reporting_period, line_code, currency, count(*) as n
from {{ ref('silver_lcr_monthly') }}
group by 1, 2, 3, 4
having count(*) > 1
