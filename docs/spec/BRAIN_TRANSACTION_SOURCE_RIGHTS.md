# Brain Transaction Control, Source Rights and Global Source Mesh

Status: implemented for issue #14 repository control layer.

This specification covers MOD-012 Transaction Control and MOD-013 Global Source Mesh. It is an execution-control layer, not a legal opinion.

## Transaction control objects

- Mandate
- IntroductionRecord
- FeeAgreement
- ReferralAgreement
- ExclusivityRecord
- OriginationEvidence
- DealRoom
- FeeControl
- GateDecision

## Source rights classes

- PUBLIC_SAFE
- PUBLIC_TERMS_RESTRICTED
- PERMISSIONED
- PAID_LICENSED
- SCRAPE_SENSITIVE
- PII_SENSITIVE
- REGULATED_DATA
- PROHIBITED

## Source planes

Corporate, licensing, regulatory, legal, financial, employment, real estate, trade, marketplaces, local government, web change, social/professional, scientific, demand, infrastructure, geospatial, procurement, events, distress and overlooked public documents.

## Hard gates

- No active connector without rights classification and provenance.
- PROHIBITED sources are REJECT.
- SCRAPE_SENSITIVE, PII_SENSITIVE and REGULATED_DATA sources are HOLD.
- PUBLIC_TERMS_RESTRICTED sources HOLD until terms are reviewed.
- PERMISSIONED sources HOLD until permission evidence exists.
- PAID_LICENSED sources HOLD until license evidence exists.
- Unknown or enhanced-risk jurisdictions HOLD for review.
- No consequential transaction disclosure without explicit operator approval.
- No fee-sensitive disclosure without mandate, fee agreement, introduction record, origination evidence and jurisdiction review.
- Legal enforceability is jurisdiction-specific and never assumed.

## Acceptance evidence

- `brain/economic_hard_gates.py`
- `tests/test_transaction_source_rights.py`
- `tests/fixtures/brain/transaction_source_rights.json`
- `reports/acceptance/ISSUE-14-transaction-source-rights.json`
- `reports/go-hold/ISSUE-14-GO-HOLD.json`
