-- Silver: the current, validated version of each LCR line.
-- Submissions with a failed blocking Bronze rule are excluded; the latest remaining version wins.
-- Earlier versions stay in Bronze (and in Iceberg snapshots) for audit.
with quarantined as (
    select distinct submission_id
    from {{ source('ops', 'dq_results') }}
    where stage = 'bronze' and severity = 'blocking' and outcome = 'FAIL'
),

eligible as (
    select b.*
    from {{ source('bronze', 'lcr_monthly') }} b
    where b.submission_id not in (select submission_id from quarantined)
),

ranked as (
    select
        e.*,
        row_number() over (
            partition by institution_id, reporting_period, line_code, currency
            order by submission_version desc, loaded_at desc
        ) as rn
    from eligible e
)

select
    institution_id,
    reporting_period,
    line_code,
    currency,
    cast(amount as decimal(20, 2)) as amount,
    submission_id,
    submission_version,
    loaded_at as bronze_loaded_at,
    current_timestamp as silver_built_at
from ranked
where rn = 1
