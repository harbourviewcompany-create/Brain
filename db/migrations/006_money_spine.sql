-- Brain v1: Money Spine
-- Commercial execution tables for immediate revenue loops.

create table if not exists money_lanes (
    id uuid primary key default gen_random_uuid(),
    lane_key text unique not null,
    title text not null,
    opportunity_class text not null,
    packaged_offer text not null,
    buyer_type text not null,
    seller_or_target_type text not null,
    first_48_hour_action text not null,
    price_low double precision not null default 0,
    price_high double precision not null default 0,
    repeatability double precision not null default 0.5 check (repeatability between 0 and 1),
    fulfillment_difficulty double precision not null default 0.5 check (fulfillment_difficulty between 0 and 1),
    time_to_cash_days double precision not null default 7,
    automation_readiness text not null default 'manual_first',
    legal_access_risk double precision not null default 0 check (legal_access_risk between 0 and 1),
    priority_score double precision not null default 0.5 check (priority_score between 0 and 1),
    status text not null default 'active' check (status in ('active','testing','scaled','paused','killed')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists money_lane_sources (
    id uuid primary key default gen_random_uuid(),
    money_lane_id uuid not null references money_lanes(id) on delete cascade,
    source_name text not null,
    source_url text,
    source_category text not null default 'manual',
    access_model text not null default 'public_or_manual',
    legal_access_status text not null default 'review_required',
    extraction_method text not null default 'manual',
    update_frequency text not null default 'unknown',
    historical_utility double precision not null default 0.5 check (historical_utility between 0 and 1),
    noise_level double precision not null default 0.5 check (noise_level between 0 and 1),
    created_at timestamptz not null default now()
);
create index if not exists money_lane_sources_lane_idx on money_lane_sources(money_lane_id);

create table if not exists money_lane_search_queries (
    id uuid primary key default gen_random_uuid(),
    money_lane_id uuid not null references money_lanes(id) on delete cascade,
    query text not null,
    channel text not null default 'web',
    purpose text not null default 'find_signals',
    created_at timestamptz not null default now()
);
create index if not exists money_lane_search_queries_lane_idx on money_lane_search_queries(money_lane_id);

create table if not exists revenue_signals (
    id uuid primary key default gen_random_uuid(),
    money_lane_id uuid references money_lanes(id),
    source_id uuid references sources(id),
    raw_signal text not null,
    named_buyer text,
    named_seller text,
    decision_maker text,
    visible_pain text,
    urgency_reason text,
    payment_path text,
    contact_channel text,
    evidence_refs jsonb not null default '[]'::jsonb,
    commercial_value double precision not null default 0.5 check (commercial_value between 0 and 1),
    confidence double precision not null default 0.5 check (confidence between 0 and 1),
    urgency double precision not null default 0 check (urgency between 0 and 1),
    contactability double precision not null default 0 check (contactability between 0 and 1),
    execution_difficulty double precision not null default 0.5 check (execution_difficulty between 0 and 1),
    legal_access_risk double precision not null default 0 check (legal_access_risk between 0 and 1),
    time_delay double precision not null default 0 check (time_delay between 0 and 1),
    status text not null default 'new' check (status in ('new','qualified','rejected','packaged','acted','closed')),
    rejection_reasons jsonb not null default '[]'::jsonb,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);
create index if not exists revenue_signals_lane_status_idx on revenue_signals(money_lane_id, status, created_at desc);
create index if not exists revenue_signals_source_idx on revenue_signals(source_id, created_at desc);

create table if not exists scored_revenue_opportunities (
    id uuid primary key default gen_random_uuid(),
    revenue_signal_id uuid not null references revenue_signals(id) on delete cascade,
    money_lane_id uuid references money_lanes(id),
    score double precision not null,
    actionable boolean not null default false,
    rejection_reasons jsonb not null default '[]'::jsonb,
    next_action text,
    created_at timestamptz not null default now()
);
create index if not exists scored_revenue_opportunities_score_idx on scored_revenue_opportunities(actionable, score desc, created_at desc);

create table if not exists packaged_offers (
    id uuid primary key default gen_random_uuid(),
    scored_opportunity_id uuid not null references scored_revenue_opportunities(id) on delete cascade,
    title text not null,
    offer_name text not null,
    buyer_type text not null,
    target_contact text not null,
    price_low double precision not null default 0,
    price_high double precision not null default 0,
    evidence_refs jsonb not null default '[]'::jsonb,
    outreach_script text not null,
    follow_up_script text not null,
    approval_required boolean not null default true,
    status text not null default 'draft' check (status in ('draft','approval_required','approved','sent','won','lost','paused')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index if not exists packaged_offers_status_idx on packaged_offers(status, created_at desc);

create table if not exists revenue_experiments (
    id uuid primary key default gen_random_uuid(),
    money_lane_id uuid references money_lanes(id),
    hypothesis text not null,
    buyer_type text not null,
    offer text not null,
    price double precision not null default 0,
    outreach_target integer not null default 30,
    success_reply_threshold integer not null default 3,
    success_paid_threshold integer not null default 1,
    kill_after_outreach integer not null default 50,
    status text not null default 'running' check (status in ('running','scale','modify','kill','paused','complete')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists revenue_experiment_results (
    id uuid primary key default gen_random_uuid(),
    experiment_id uuid not null references revenue_experiments(id) on delete cascade,
    outreach_sent integer not null default 0,
    replies integer not null default 0,
    meetings integer not null default 0,
    paid_conversions integer not null default 0,
    revenue double precision not null default 0,
    operator_hours double precision not null default 0,
    decision text not null check (decision in ('scale','modify','kill','continue')),
    lesson text not null,
    created_at timestamptz not null default now()
);

create table if not exists daily_revenue_reports (
    id uuid primary key default gen_random_uuid(),
    report_date date not null default current_date,
    raw_signals_reviewed integer not null default 0,
    signals_logged integer not null default 0,
    qualified_opportunities integer not null default 0,
    prioritized_opportunities integer not null default 0,
    direct_revenue_actions integer not null default 0,
    sellable_assets_created integer not null default 0,
    lessons_recorded integer not null default 0,
    passed boolean not null default false,
    gaps jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now(),
    unique(report_date)
);

alter table money_lanes enable row level security;
alter table money_lane_sources enable row level security;
alter table money_lane_search_queries enable row level security;
alter table revenue_signals enable row level security;
alter table scored_revenue_opportunities enable row level security;
alter table packaged_offers enable row level security;
alter table revenue_experiments enable row level security;
alter table revenue_experiment_results enable row level security;
alter table daily_revenue_reports enable row level security;

revoke all on table money_lanes from anon, authenticated;
revoke all on table money_lane_sources from anon, authenticated;
revoke all on table money_lane_search_queries from anon, authenticated;
revoke all on table revenue_signals from anon, authenticated;
revoke all on table scored_revenue_opportunities from anon, authenticated;
revoke all on table packaged_offers from anon, authenticated;
revoke all on table revenue_experiments from anon, authenticated;
revoke all on table revenue_experiment_results from anon, authenticated;
revoke all on table daily_revenue_reports from anon, authenticated;
