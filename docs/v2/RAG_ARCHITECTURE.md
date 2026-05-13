# RAG Architecture (V2 Target)

## Purpose

Define the target FastAPI RAG architecture and migration direction aligned with v2 database-first refactor.

## Architecture goals

- Keep runtime stable for Node integration.
- Separate concerns between API layer, retrieval pipeline, provider logic, and data build/indexing.
- Establish `rag_knowledge_base` as the knowledge source of truth.
- Keep BM25/vector indexes as derived runtime artifacts.

## Target architecture style

### Route layer (FastAPI)

- HTTP concerns only:
  - request/response validation
  - auth/internal-key middleware application
  - error envelope handling
- No retrieval/generation orchestration inside route handlers.

### Service layer

- Application services orchestrate:
  - retrieval execution
  - grounding/context building
  - provider invocation
  - fallback policy
  - output shaping

### Retrieval pipeline layer

- Encapsulate:
  - retrievers (BM25/vector/hybrid)
  - reranking/scoring
  - context assembly
- Independent from provider SDK specifics.

### Provider layer

- Gemini provider isolated behind provider interface/adapter.
- Fallback strategy lives in service/pipeline policy, not SDK wrapper code.
- Provider can be replaced without changing routes.

### Repository/data-access layer

- Clear separation of:
  - runtime artifact loaders
  - corpus export inputs
  - optional future DB-backed readers

## Source-of-truth model

- `rag_knowledge_base` is canonical knowledge data source.
- BM25/vector files are build outputs generated from canonical corpus.
- Runtime behavior should be reproducible from source-of-truth exports.

## RAG data migration direction (required order)

1. **Do not switch runtime to direct MySQL reads first.**
2. Export `rag_knowledge_base` into corpus files (JSONL/parquet as needed).
3. Build BM25/vector index artifacts from that corpus.
4. Keep runtime serving from index artifacts for initial cutover.
5. Consider direct DB-backed online retrieval later only if needed.

## Suggested logical module layout

```text
backend/rag/
  app/
    main.py
    routers/
      health.py
      rag.py
      ai_itinerary.py
      admin.py
    schemas/
  services/
    rag_service.py
    itinerary_service.py
  pipelines/
    retrieval_pipeline.py
    grounding_pipeline.py
  retrievers/
    bm25_retriever.py
    vector_retriever.py
    hybrid_retriever.py
  providers/
    gemini_provider.py
    template_provider.py
  repositories/
    corpus_repository.py
    artifact_repository.py
  jobs/
    export_from_rag_kb.py
    build_indexes.py
```

This is a target design reference and does not require immediate file movement.

## Runtime contract expectations

- Node-facing APIs (`/rag/chat/simple`, `/rag/chat`, `/ai/itinerary-*`) remain stable during internal refactor.
- Returned recommendation metadata can include `rawPlaceId`/`place_key`, but persistence id resolution stays in Node.

