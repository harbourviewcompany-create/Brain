# Resource-Bounded Continuous Developmental Scheduler

Status: repository implementation GO subject to exact-head CI. Self-approval, autonomous code mutation, merge, deploy, spending and external action remain HOLD.

The scheduler is an AGENT-021 control layer above the governed AGENT-020 improvement cycle. It may decide that a capability assessment is due; it may not authorize an optimization plan or experiment.

## Objects

- `DevelopmentalSchedule`
- `DevelopmentalBudget`
- `DevelopmentalBackoffState`
- `DevelopmentalQueueItem`
- `DevelopmentalRunRequest`
- `DevelopmentalRunRecord`

All six are persisted as typed records in the AGENT-019 developmental evidence ledger. No parallel scheduler database is authoritative.

## Scheduling

Due work is ranked from configured priority, evidence staleness and regression risk. Active backoff removes a capability from the runnable queue. A run is created only after CPU/time, token and API-cost-style abstract budget capacity is available.

## Failure behavior

Failures create exponential bounded backoff. Repeated failures cannot hot-loop. Scheduler state is replayable because every state transition is appended to the developmental evidence ledger.

## Authority boundary

The only developmental-cycle method invoked by scheduler execution is `assess_capability`. Proposal, plan authorization, experiment authorization, promotion, repository mutation, merge, deployment, spending and external action are not scheduler authority.

## Restart

`DevelopmentalReplayService` reconstructs schedule, budget, queue, run and backoff records. A restarted `DevelopmentalSchedulerService` derives current state from those replayed records.
