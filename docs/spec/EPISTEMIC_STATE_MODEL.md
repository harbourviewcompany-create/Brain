# Epistemic State Model

Confidence remains supported but is not sufficient to represent what Brain knows.

## Dimensions
- confidence: current subjective support, [0,1]
- uncertainty: unresolved uncertainty, [0,1]
- evidence_strength: directness/quality of evidence, [0,1]
- evidence_diversity: independence/diversity of support, [0,1]
- source_reliability: reliability of contributing sources, [0,1]
- contradiction: unresolved contradictory support, [0,1]
- recency: currentness of evidence/state, [0,1]
- causal_support: evidence for causal rather than correlational relation, [0,1]
- prediction_performance: resolved predictive performance, [0,1]
- calibration: confidence-outcome calibration, [0,1]
- stability: resistance to small evidence perturbations, [0,1]
- novelty: departure from established model state, [0,1]

Optional dimensions may be absent when unsupported; absence is not zero.

## Rules
1. Confidence may never erase the component dimensions.
2. Contradictory evidence remains linked and visible.
3. Derived scores must preserve formula/provenance references where consequential.
4. Recency is time-dependent and may decay without deleting historical evidence.
5. Epistemic state is descriptive, not external-action authorization.
6. Biological/mechanistic uncertainty links to the existing Unknown Mechanism Registry when applicable.

## Uses
Attention may use uncertainty/novelty; curiosity may use uncertainty and information-value gaps; belief update may alter confidence while retaining contradiction; planning may use causal support; governance may require minimum evidence/calibration for consequential projection.