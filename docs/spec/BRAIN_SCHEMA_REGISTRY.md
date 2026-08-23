# Brain Schema Registry

Agents must implement exact schemas before runtime loops are accepted.

## Required objects

Source, Sensor, RawObservation, PerceptualEvent, SalienceAssessment, AttentionDecision, EvidenceItem, Entity, Belief, BeliefContradiction, Signal, Opportunity, CandidateAction, ActionSimulation, ApprovalRequest, ApprovalDecision, ExecutedAction, Outcome, Prediction, AgencyAttribution, RewardEvent, PainEvent, GraphNode, GraphEdge, GraphWeightUpdate, MemoryObject, FormulaRegistryEntry, FormulaRun, DecisionExplanation, AcceptanceReport, AuditEvent.

## Common required fields

- `id`
- `created_at`
- `status`
- `source_ids` where applicable
- `parent_id` where applicable
- `formula_run_ids` where scored
- `audit_event_ids` where transitioned

## TypeScript pattern

```ts
export interface BrainObject {
  id: string;
  created_at: string;
  status: string;
}
```

## Zod pattern

```ts
export const BrainObjectSchema = z.object({
  id: z.string().min(1),
  created_at: z.string(),
  status: z.string().min(1)
});
```

## Validation rules

- IDs are required.
- Scores require formula runs.
- Outcomes require action links.
- Reward and pain require attribution.
- External actions require approval.
- Blocked evidence cannot update semantic memory.

## Storage

V0 may use in-memory or JSON-backed storage. Production targets PostgreSQL as canonical event ledger with graph projection rebuildable from events.