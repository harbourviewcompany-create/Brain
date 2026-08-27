-- Per-source reliability learning for the revenue execution spine.
-- MoneySpineService.source_scores previously existed only in memory —
-- every restart erased which sources had proven reliable for revenue,
-- which is exactly the kind of learning that's supposed to compound
-- over time. No table for it existed anywhere in this migration set
-- until now; brain/adapters/revenue_store.py is the first adapter to
-- read/write it.

create table if not exists revenue_source_scores (
    source_id text primary key,
    score double precision not null default 0.5 check (score between 0 and 1),
    updated_at timestamptz not null default now()
);

alter table revenue_source_scores enable row level security;
revoke all on table revenue_source_scores from anon, authenticated;
