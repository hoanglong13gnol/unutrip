# V2 Refactor Phase Plan

## Strategy

Use the strangler pattern:

- Keep existing endpoints and Android contract stable.
- Replace internals progressively behind repository/service layers.
- Migrate one read/write concern at a time with parity checks.

## Cross-phase safeguards

- No full rewrite in one batch.
- Contract/smoke checks after each phase.
- Ability to pause/rollback per module path.
- Prefer feature-flagged switches for data-source cutover where helpful.

## Phase 1 - Backend repository/service extraction (legacy behavior unchanged)

- Extract inline SQL from routes/helpers into repositories.
- Introduce services for workflow orchestration.
- Keep current legacy table usage and output behavior unchanged.

Exit criteria:

- No API contract changes.
- Route tests/smoke checks remain green.

## Phase 2 - Switch place/image read paths to v2 DB tables

- Move place reads from `destinations` to `app_places`.
- Move image reads from `destination_images` to `place_images`.
- Keep DTO/output shape unchanged.

Exit criteria:

- `/destinations`, featured, nearby, detail parity checks pass.
- Image behavior parity checks pass.

## Phase 3 - Switch rawPlaceId resolution to `place_id_map`

- Replace `rag_places.place_id -> destination_id` runtime mapping in Node persistence flows.
- Ensure unresolved-id handling remains explicit and safe.

Exit criteria:

- AI itinerary save paths resolve ids with equal or better success rate.
- No orphan itinerary item writes.

## Phase 4 - Switch review aggregate target to `app_places`

- Keep aggregate source from `reviews`.
- Update aggregate write target from legacy place table to `app_places`.

Exit criteria:

- Rating/reviewCount parity checks pass.
- Android-visible rating behavior unchanged.

## Phase 5 - RAG export/index build from `rag_knowledge_base`

- Export canonical corpus from `rag_knowledge_base`.
- Build BM25/vector artifacts from exported corpus.
- Keep runtime retrieval artifact-driven (no direct DB runtime read yet).

Exit criteria:

- RAG route parity and retrieval quality checks pass.
- Runtime readiness/index build checks pass.

## Phase 6 - AI itinerary and chatbot parity tests

- Verify Node↔RAG integration contracts.
- Validate suggestion quality/coverage and fallback behavior.
- Confirm itinerary save flow correctness with id resolution.

Exit criteria:

- Functional parity accepted for chat + itinerary generation workflows.

## Phase 7 - Admin cleanup

- Refactor admin monolith into module-aligned structure.
- Decide admin migration scope to v2 sources for this release window.

Exit criteria:

- Admin critical functions preserved.
- No impact on Android API contract.

## Phase 8 - Android polish after API stability

- Only after backend contract stability is confirmed.
- Android-side cleanup/tuning for any non-breaking improvements.

Exit criteria:

- End-to-end user flows remain stable in staging/production-like environments.

## Open questions

- Should Node call `AI_MODEL_URL` directly, or use FastAPI RAG as the single AI gateway?
- Is a backend feature flag such as `USE_V2_PLACE_TABLES` required for controlled rollout?
- Should admin migration be in this release scope or deferred?
- Should RAG remain index-artifact runtime long term, or later adopt DB-backed online retrieval?

