# Backend Architecture (V2 Target)

## Purpose

Define the target Node backend architecture for UNUtrip v2 while preserving Android API compatibility during migration.

## Current context

- v2 DB migrations are validated on `unudata_v2_test`.
- Backend runtime still reads legacy tables (`destinations`, `destination_images`, `rag_places`) in multiple routes/helpers.
- Android clients already depend on current API response shapes and endpoint behavior.

## Target architecture style

Adopt a modular layered architecture:

- **Routes/Controllers**
  - HTTP-only responsibilities: request parsing, auth middleware, validation handoff, response return.
  - No business logic and no inline SQL.
- **Services**
  - Business workflows and orchestration.
  - Transaction boundaries for multi-step writes.
  - Cross-module coordination (for example AI suggestion -> id resolution -> itinerary save flow).
- **Repositories**
  - SQL-only data access.
  - Table/query ownership and reusable query methods.
  - No HTTP or DTO formatting.
- **Mappers/DTO**
  - Output contract protection for Android.
  - Stable field naming, nullability, and response envelope compatibility.

## Migration-first structure principle

Use a strangler approach:

- Keep existing route files/endpoints initially.
- Move internals behind repository/service/mapper layers first.
- Avoid immediate route/file rewrites.
- Change route internals incrementally, one path at a time.

## V2 DB direction for backend reads/writes

### Read path transitions

- `destinations` read paths -> `app_places`
- `destination_images` read paths -> `place_images`
- `rag_places` rawPlaceId resolution -> `place_id_map`

### Rules

- `rag_knowledge_base` is **not** an Android app place API source.
- Android-facing place APIs should remain app-domain (`app_places` + `place_images`) not knowledge-domain.
- API response shape must remain stable while data source moves.

## Module ownership model (Node)

- `places` module
  - Place list/featured/nearby/detail reads from app-domain tables.
- `favorites` module
  - User favorite workflows, app place existence checks.
- `reviews` module
  - Review writes and rating aggregate updates.
- `itineraries` module
  - Transactional itinerary persistence and retrieval.
- `ai` module
  - RAG integration orchestration and rawPlaceId/place_key resolution prior to persistence.
- `auth/users` modules
  - Auth/profile concerns only.
- `admin` module
  - Admin-only concerns, isolated from Android API logic.

## Compatibility guardrails

- Preserve existing endpoint paths.
- Preserve existing response envelope semantics (`success`, `data`, paging fields, etc.).
- Preserve destination DTO field names/types expected by Android.
- Add contract checks before and after each data-source switch.

## Recommended target folder pattern (logical)

```text
backend/nodejs/src/
  modules/
    places/
      places.controller.js
      places.service.js
      places.repository.js
      places.mapper.js
    favorites/
    reviews/
    itineraries/
    ai/
    auth/
    users/
    admin/
  shared/
    db/
    errors/
    validation/
    dto/
```

This pattern is a target direction, not a required immediate file move.

