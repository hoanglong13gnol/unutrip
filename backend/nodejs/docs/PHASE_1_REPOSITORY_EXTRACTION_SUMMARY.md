# Phase 1 Repository Extraction Summary

## Scope

Phase 1 focused on backend SQL extraction from route/helper internals into repository modules while preserving legacy behavior and Android API compatibility.

## Completed Extractions

The following SQL extraction work is completed and committed:

- `helpers.js` SQL extraction completed.
- `destinations.routes.js` SQL extraction completed.
- `favorites.routes.js` SQL extraction completed.
- `reviews.routes.js` SQL extraction completed.
- `itineraries.routes.js` SQL extraction completed.
- `ai.routes.js` SQL extraction completed.
- `auth.routes.js` and `users.routes.js` SQL extraction completed.

## Repositories Now Available

Current repository layer under `backend/nodejs/src/repositories/`:

- `ai.repository.js`
- `destinationImages.repository.js`
- `destinations.repository.js`
- `favorites.repository.js`
- `itineraries.repository.js`
- `ragPlaces.repository.js`
- `reviews.repository.js`
- `users.repository.js`

## What Remains Legacy

Backend runtime remains on legacy table sources in this phase:

- `destinations`
- `destination_images`
- `rag_places`
- `users`
- `favorites`
- `reviews`
- `itineraries`
- `itinerary_days`
- `itinerary_items`

No switch to v2 app-domain tables has been applied yet (`app_places`, `place_images`, `place_id_map`).

## What Did Not Change

Phase 1 intentionally kept behavior stable:

- **API paths:** unchanged.
- **Android response contract:** unchanged (envelopes, field names, DTO expectations).
- **DB table source:** unchanged (still legacy tables).
- **RAG runtime behavior:** unchanged (existing Node ↔ FastAPI RAG integration and fallback paths preserved).

## Smoke Test Result

- Backend starts successfully.
- Health endpoint returns:
  - `{"ok":true,"name":"smarttravel-backend"}`

## Admin.js Audit Decision

`admin.js` was audited during Phase 1.

Decision:

- Full refactor is **deferred**.
- Reason: high-risk monolith, mixed concerns (HTML rendering + SQL + RAG admin proxy), and not Android runtime critical.
- Admin cleanup should be handled in a later dedicated admin cleanup/security phase.

## Recommended Next Phase

Two safe options for immediate follow-up:

1. **Phase 2 preparation path (recommended first):**
   - Plan controlled v2 table switch strategy.
   - Define parity/contract checks for `destinations` -> `app_places`, `destination_images` -> `place_images`, and later `rag_places` -> `place_id_map`.

2. **Service layer extraction path (parallel-friendly):**
   - Introduce service orchestration for multi-step write flows and transaction boundaries while preserving current behavior.

Suggested execution order:

- First formalize switch/parity plan and guardrails.
- Then perform controlled Phase 2 read-path cutover with compatibility verification.
