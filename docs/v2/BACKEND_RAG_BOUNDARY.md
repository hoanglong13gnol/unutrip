# Backend and RAG Boundary (V2)

## Purpose

Define clear ownership boundaries between Node backend and FastAPI RAG to reduce coupling and migration risk.

## Ownership split

## Node backend owns

- Authentication and authorization.
- User domain (`users`).
- App transactional domains:
  - `favorites`
  - `reviews`
  - `itineraries` and `itinerary_items`
- Android DTO/API contract stability.
- Database transactions for persistence flows.
- rawPlaceId/place_key resolution for persistence using `place_id_map`.

## RAG service owns

- Retrieval (BM25/vector/hybrid).
- Ranking and grounding context assembly.
- Prompt construction/generation orchestration.
- Gemini provider invocation and fallback behavior.
- Itinerary suggestion generation (recommendations/options), not final persistence.

## Data exchange contract

RAG may return:

- `rawPlaceId`
- `place_key`
- recommendation metadata (score/reasons/context hints)

Node must:

- resolve identifiers to `app_places.id` via `place_id_map` before writes.
- validate persistence candidates.
- write final rows into app transactional tables.

## Explicit prohibitions

RAG must **not**:

- write `users`, `favorites`, `reviews`, or final itinerary persistence.
- own Android response-shape decisions.

Node must **not**:

- treat RAG as source of truth for app rating aggregates.
- bypass `place_id_map` when converting raw recommendation ids for persistence.

## Table boundary guidance

- Node app APIs: `app_places`, `place_images`, `place_id_map` (for id resolution), plus user/itinerary/review/favorite tables.
- RAG knowledge pipeline: `rag_knowledge_base` as canonical content source, exported into retrieval artifacts.

`rag_knowledge_base` is not an Android app places API source.

## Integration principles

- Contract-first integration between Node and RAG APIs.
- Version compatibility maintained via stable request/response schema.
- Fail-safe behavior:
  - If RAG suggestion ids cannot resolve, Node returns clear unresolved diagnostics and avoids partial invalid persistence.

