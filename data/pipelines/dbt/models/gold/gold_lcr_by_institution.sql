-- Gold: LCR per institution and period (simplified formula for the POC; no Level 2 caps).
--   LCR = weighted HQLA / (outflows - min(inflows, 75% of outflows))
with s as (
    select * from {{ ref('silver_lcr_monthly') }}
),

w as (
    select line_code, category, cast(weight as double) as weight
    from {{ source('reference', 'lcr_line_codes') }}
),

agg as (
    select
        s.institution_id,
        s.reporting_period,
        sum(case when w.category = 'HQLA' then cast(s.amount as double) * w.weight end) as hqla,
        sum(case when w.category = 'OUTFLOW' then cast(s.amount as double) end) as outflows,
        sum(case when w.category = 'INFLOW' then cast(s.amount as double) end) as inflows,
        array_join(array_agg(distinct s.submission_id), ',') as submission_ids
    from s
    join w on s.line_code = w.line_code
    group by 1, 2
)

select
    a.institution_id,
    i.institution_name,
    i.institution_type,
    i.peer_group,
    a.reporting_period,
    round(a.hqla, 2) as hqla,
    round(a.outflows, 2) as outflows,
    round(a.inflows, 2) as inflows,
    round(a.outflows - least(a.inflows, 0.75 * a.outflows), 2) as net_outflows,
    round(a.hqla / nullif(a.outflows - least(a.inflows, 0.75 * a.outflows), 0), 4) as lcr_ratio,
    a.submission_ids,
    current_timestamp as gold_built_at
from agg a
left join {{ source('reference', 'institutions') }} i
    on a.institution_id = i.institution_id
