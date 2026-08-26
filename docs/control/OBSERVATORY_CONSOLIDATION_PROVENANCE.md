# Brain Observatory consolidation provenance

Status: REVIEW / repository consolidation candidate. Production remains HOLD.

Canonical repository: `harbourviewcompany-create/Brain`
Canonical application path: `apps/observatory`
Preserved source repository: `harbourviewcompany-create/brain-control-plane`
Preserved source commit: `03e3c462ff8f8233033457fc703c418d21200b32`
Brain consolidation base: `28949d971becd1c9fcfa8607ef83f51ee4c8d980`

The split repository is treated as an accidental repository boundary, not a separate product. Its complete Next.js application tree is copied into `apps/observatory`; its Observatory documentation is copied to `docs/observatory`; its verification workflows are adapted to the canonical Brain repository. No production deployment, Vercel project mutation, domain mutation, Railway mutation, database write, or archive/delete action against the split repository is part of this change.

Intentional adaptations from the preserved source are limited to canonical path/repository metadata, the package name, verification working directories, Brain control traceability, and protected CI integration. Runtime UI/BFF source under `apps/observatory/src` is otherwise preserved from the cited source commit.

Retirement gate for `brain-control-plane`: consolidated Brain PR green; source-to-destination inventory verified; Vercel Git integration rewired to Brain/main with Root Directory `apps/observatory`; production domain/env/OIDC identity retained; production parity audit green; only then archive/retire the split repository in a separate explicitly authorized action.
