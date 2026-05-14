import { z } from "zod";

/** One place row from FastAPI `rag_chat_simple` (see backend/rag/services/rag_service.py). */
export const ragChatSimplePlaceSchema = z
  .object({
    place_id: z.union([z.string(), z.number()]).optional().nullable(),
    name: z.string().optional().nullable(),
    province: z.string().optional().nullable(),
    city: z.string().optional().nullable(),
    area: z.string().optional().nullable(),
    category_main: z.string().optional().nullable(),
    category_sub: z.string().optional().nullable(),
    budget_level: z.string().optional().nullable(),
    walking_level: z.string().optional().nullable(),
    kid_friendly: z.boolean().optional().nullable(),
    elderly_friendly: z.boolean().optional().nullable(),
    slot: z.string().optional().nullable(),
    quality_score: z.union([z.number(), z.string()]).optional().nullable(),
    recommended_use: z.string().optional().nullable(),
    requires_realtime_check: z.boolean().optional().nullable(),
    score: z.union([z.number(), z.string()]).optional().nullable()
  })
  .passthrough();

const latencyValueSchema = z.union([z.number(), z.string(), z.null()]);

export const ragChatSimpleResponseSchema = z
  .object({
    answer: z.union([z.string(), z.null()]).optional(),
    places: z.array(ragChatSimplePlaceSchema).optional(),
    warnings: z.array(z.string()).optional(),
    latency_ms: z.record(latencyValueSchema).optional(),
    model_used: z.string().optional(),
    fallback_used: z.boolean().optional(),
    rag_mode: z.string().optional(),
    runtime_mode: z.union([z.string(), z.null()]).optional()
  })
  .passthrough();

/**
 * Normalize FastAPI `/rag/chat/simple` JSON for Node callers.
 * Invalid shapes get safe defaults; issues are listed for logging/metrics.
 *
 * @param {unknown} raw
 * @returns {{ ok: true, data: object, issues: string[] } | { ok: false, data: null, issues: string[] }}
 */
export function normalizeRagChatSimpleResponse(raw) {
  const parsed = ragChatSimpleResponseSchema.safeParse(raw);
  if (parsed.success) {
    const d = parsed.data;
    return {
      ok: true,
      data: {
        answer: d.answer ?? "",
        places: Array.isArray(d.places) ? d.places : [],
        warnings: Array.isArray(d.warnings) ? d.warnings : [],
        latency_ms: d.latency_ms && typeof d.latency_ms === "object" ? d.latency_ms : {},
        model_used: d.model_used ?? "unknown",
        fallback_used: d.fallback_used ?? false,
        rag_mode: d.rag_mode ?? "balanced",
        runtime_mode: d.runtime_mode ?? null
      },
      issues: []
    };
  }

  const issues = parsed.error.issues.map((i) => `${i.path.join(".") || "(root)"}: ${i.message}`);

  const loose = raw && typeof raw === "object" ? /** @type {Record<string, unknown>} */ (raw) : {};
  return {
    ok: false,
    data: {
      answer: typeof loose.answer === "string" ? loose.answer : "",
      places: Array.isArray(loose.places) ? loose.places : [],
      warnings: Array.isArray(loose.warnings)
        ? loose.warnings.filter((w) => typeof w === "string")
        : [],
      latency_ms: loose.latency_ms && typeof loose.latency_ms === "object" ? loose.latency_ms : {},
      model_used: typeof loose.model_used === "string" ? loose.model_used : "unknown",
      fallback_used: typeof loose.fallback_used === "boolean" ? loose.fallback_used : false,
      rag_mode: typeof loose.rag_mode === "string" ? loose.rag_mode : "balanced",
      runtime_mode:
        typeof loose.runtime_mode === "string" || loose.runtime_mode === null
          ? loose.runtime_mode
          : null
    },
    issues
  };
}
