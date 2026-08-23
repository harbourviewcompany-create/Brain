# Brain Runtime Loops

## Ingestion loop

Input -> Source -> RawObservation -> access review -> content hash -> audit event.

Acceptance: every observation has source, status, and provenance.

## Perception loop

RawObservation -> PerceptualEvent -> salience -> attention -> route.

Acceptance: every event has route and attention decision.

## Belief update loop

Evidence -> entity resolution -> belief prior -> formula run -> posterior -> contradiction check.

Acceptance: every update has evidence and formula trace.

## Opportunity loop

Signal -> opportunity candidate -> score -> kill rules -> next state.

Acceptance: no opportunity without evidence.

## Action simulation loop

Opportunity -> candidate actions -> expected utility -> trust-adjusted value -> go/no-go.

Acceptance: external actions go to approval.

## Approval loop

CandidateAction -> ApprovalRequest -> decision -> execution permission.

Acceptance: no external consequence without approval record.

## Outcome learning loop

ExecutedAction -> Outcome -> PredictionError -> AgencyAttribution -> Reward/Pain -> GraphUpdate.

Acceptance: no major learning without attribution.

## Consolidation loop

Events -> memory candidates -> contradiction review -> stale decay -> daily report.

Acceptance: no evidence deletion without audit.

## Strategy loop

Outcomes -> performance metrics -> anti-gaming review -> mutation proposal -> rollback rule.

Acceptance: no mutation without test window.

## Recovery loop

Incident -> freeze affected lane -> preserve evidence -> cause review -> safeguard -> recovery report.

Acceptance: severe incident cannot be silently ignored.