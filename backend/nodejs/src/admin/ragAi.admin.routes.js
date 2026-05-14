/**
 * Admin section router: RAG AI dashboard + RAG action proxies.
 *
 * Phase 4 split — handler bodies (including the giant HTML template returned
 * by `GET /rag-ai`) are byte-identical copies of the original blocks in the
 * old `src/admin.js`. Shared helpers moved into `./_shared/*.js`:
 *  - `escapeHtml`, `renderJsonBox` from `./_shared/escape.js`,
 *  - `renderLayout` from `./_shared/layout.js`,
 *  - `fetchRagJson`, `postRagJson` from `./_shared/ragHttp.js`.
 */

import { RAG_ADMIN_DEBUG_TIMEOUT_MS, RAG_BASE_URL } from "../config/env.js";
import { fillAdminTemplate, loadAdminTemplate, scriptNonceAttr } from "./_shared/adminTemplate.js";
import { escapeHtml, renderJsonBox } from "./_shared/escape.js";
import { renderLayout } from "./_shared/layout.js";
import { fetchRagJson, postRagJson } from "./_shared/ragHttp.js";

export function registerRagAiAdminRoutes(router) {
      // 5. RAG AI Dashboard
  router.get("/rag-ai", async (req, res) => {
    try {
      const [overview, ragStatus, selfTest, metrics, dataQuality] = await Promise.all([
        fetchRagJson("/admin/system/overview"),
        fetchRagJson("/admin/rag/status"),
        fetchRagJson("/admin/system/self-test"),
        fetchRagJson("/admin/ai/metrics"),
        fetchRagJson("/admin/data-quality/status")
      ]);

      const readyValue =
        ragStatus.data?.ready ??
        ragStatus.data?.status ??
        ragStatus.data?.rag_ready ??
        overview.data?.ready ??
        overview.data?.status ??
        selfTest.data?.ready ??
        "unknown";

      const passedValue =
        selfTest.data?.passed ??
        selfTest.data?.summary?.passed ??
        selfTest.data?.tests_passed ??
        "N/A";

      const failedValue =
        selfTest.data?.failed ??
        selfTest.data?.summary?.failed ??
        selfTest.data?.tests_failed ??
        "N/A";
        const dqScan = dataQuality.data?.scan ?? {};
const dqAutofix = dataQuality.data?.autofix ?? {};
const dqReviewed = dataQuality.data?.reviewed ?? {};
const st = selfTest.data ?? {};
const stChecks = st.checks ?? {};
const rs = ragStatus.data ?? {};
const rsFiles = rs.files ?? {};
const overviewRag = overview.data?.rag ?? {};
const rsStore = rs.place_store ?? overviewRag.place_store ?? {};
const overviewRuntime = overview.data?.runtime ?? {};
const overviewCache = overview.data?.cache ?? {};
const aiMetrics = metrics.data ?? {};
const modelUsage = aiMetrics.model_usage ?? {};

      const ragFilesGrid = [
        ["places_master", rsFiles.places_master],
        ["places_app", rsFiles.places_app],
        ["places_app_reviewed", rsFiles.places_app_reviewed],
        ["places_itinerary", rsFiles.places_itinerary],
        ["rag_documents", rsFiles.rag_documents],
        ["bm25_index", rsFiles.bm25_index]
      ]
        .map(
          ([label, file]) => `
                <div class="bg-white border border-blue-100 rounded-xl px-4 py-3">
                    <div class="flex items-center justify-between mb-1">
                        <span class="text-xs font-bold text-slate-600">${escapeHtml(label)}</span>
                        <span class="text-xs font-extrabold ${file?.exists ? "text-emerald-600 bg-emerald-50" : "text-red-600 bg-red-50"} px-2 py-1 rounded-lg">${escapeHtml(file?.exists ?? "N/A")}</span>
                    </div>
                    <p class="text-[11px] text-gray-400 font-medium truncate">${escapeHtml(file?.path ?? "")}</p>
                    <p class="text-[11px] text-blue-600 font-extrabold mt-1">${escapeHtml(file?.size_mb ?? "N/A")} MB</p>
                </div>
            `
        )
        .join("");

      const selfTestChecksGrid = [
        ["Health OK", stChecks.health_ok?.ok],
        ["RAG files ready", stChecks.rag_files_ready?.ok],
        ["Place store ready", stChecks.place_store_ready?.ok],
        ["Using reviewed dataset", stChecks.place_store_using_reviewed?.ok],
        ["Cache OK", stChecks.cache_ok?.ok],
        ["Data quality report OK", stChecks.data_quality_report_ok?.ok],
        ["Retrieve Khánh Hòa OK", stChecks.retrieve_khanhhoa_ok?.ok],
        ["Retrieve Huế OK", stChecks.retrieve_hue_ok?.ok]
      ]
        .map(
          ([label, ok]) => `
                <div class="flex items-center justify-between bg-white border border-emerald-100 rounded-xl px-4 py-3">
                    <span class="text-xs font-bold text-slate-600">${escapeHtml(label)}</span>
                    <span class="text-xs font-extrabold ${ok ? "text-emerald-600 bg-emerald-50" : "text-red-600 bg-red-50"} px-2 py-1 rounded-lg">${escapeHtml(ok ?? "N/A")}</span>
                </div>
            `
        )
        .join("");

      const dqIssueTypesGrid = Object.entries(dqScan.issue_counts || {})
        .map(
          ([key, value]) => `
                    <div class="flex items-center justify-between bg-gray-50 rounded-xl px-4 py-3">
                        <span class="text-xs font-bold text-slate-600">${escapeHtml(key)}</span>
                        <span class="text-xs font-extrabold text-orange-600 bg-orange-100 px-2 py-1 rounded-lg">${escapeHtml(value)}</span>
                    </div>
                `
        )
        .join("");

      const cspNonce = res.locals.cspNonce;
      const content = fillAdminTemplate(loadAdminTemplate("ragAi.content.html"), {
        RAG_BASE_URL_ESC: escapeHtml(RAG_BASE_URL),
        KPI_READY_CLASS:
          readyValue === true || readyValue === "true" ? "text-emerald-600" : "text-red-500",
        READY_VALUE_ESC: escapeHtml(readyValue),
        SELF_TEST_RATIO_ESC: `${escapeHtml(passedValue)}/${escapeHtml(Number(passedValue) + Number(failedValue || 0))}`,
        RS_PLACE_COUNT_ESC: escapeHtml(rsStore.place_count ?? "N/A"),
        RS_REVIEWED_CLASS: rsStore.using_reviewed ? "text-emerald-600" : "text-orange-500",
        RS_REVIEWED_ESC: escapeHtml(rsStore.using_reviewed ?? "N/A"),
        BM25_TOP_CLASS: rsFiles.bm25_index?.exists ? "text-emerald-600" : "text-red-500",
        BM25_EXISTS_ESC: escapeHtml(rsFiles.bm25_index?.exists ?? "N/A"),
        RAG_STATUS_OK_CLASS: ragStatus.ok ? "text-emerald-600" : "text-red-500",
        RAG_STATUS_HTTP: ragStatus.status,
        FAILED_KPI_CLASS: Number(failedValue) > 0 ? "text-red-500" : "text-emerald-600",
        FAILED_VALUE_ESC: escapeHtml(failedValue),
        PASSED_VALUE_ESC: escapeHtml(passedValue),
        SELF_TEST_URL_ESC: escapeHtml(selfTest.url),
        READY_LINE_ESC: escapeHtml(readyValue),
        CHECKLIST_SELF_ESC: `${escapeHtml(passedValue)} passed / ${escapeHtml(failedValue)} failed`,
        PLACE_STORE_PLACES_ESC: `${escapeHtml(rsStore.place_count ?? "N/A")} places`,
        BM25_LINE_ESC: `${escapeHtml(rsFiles.bm25_index?.exists ?? "N/A")} · ${escapeHtml(rsFiles.bm25_index?.size_mb ?? "N/A")} MB`,
        DQ_ISSUES_LINE_ESC: `${escapeHtml(dqScan.issue_count ?? "N/A")} issues · ${escapeHtml(dqAutofix.changed_count ?? "N/A")} autofix`,
        OVERVIEW_OK_CLASS: overview.ok ? "text-emerald-600" : "text-red-500",
        OVERVIEW_HTTP: overview.status,
        RUNTIME_MODE_ESC: escapeHtml(overviewRuntime.runtime_mode ?? "N/A"),
        GEMINI_EN_CLASS: overviewRuntime.enable_gemini ? "text-emerald-600" : "text-orange-500",
        GEMINI_EN_ESC: escapeHtml(overviewRuntime.enable_gemini ?? "N/A"),
        GEMINI_MODEL_ESC: escapeHtml(overviewRuntime.gemini_model ?? "N/A"),
        GEMINI_CFG_CLASS: overviewRuntime.gemini_configured ? "text-emerald-600" : "text-red-500",
        GEMINI_CFG_ESC: escapeHtml(overviewRuntime.gemini_configured ?? "N/A"),
        ORAG_READY_CLASS: overviewRag.ready ? "text-emerald-600" : "text-red-500",
        ORAG_READY_ESC: escapeHtml(overviewRag.ready ?? "N/A"),
        CACHE_EN_CLASS: overviewCache.enabled ? "text-emerald-600" : "text-orange-500",
        CACHE_EN_ESC: escapeHtml(overviewCache.enabled ?? "N/A"),
        OVERVIEW_JSON_BOX: renderJsonBox(overview.data),
        RS_READY_CLASS: rs.ready ? "text-emerald-600" : "text-red-500",
        RS_READY_ESC: escapeHtml(rs.ready ?? "N/A"),
        RAG_FILES_GRID: ragFilesGrid,
        RAG_STATUS_JSON_BOX: renderJsonBox(ragStatus.data),
        ST_HDR_OK_CLASS: selfTest.ok ? "text-emerald-600" : "text-red-500",
        SELF_TEST_HTTP: selfTest.status,
        ST_READY_CLASS: st.ready ? "text-emerald-600" : "text-red-500",
        ST_READY_ESC: escapeHtml(st.ready ?? "N/A"),
        ST_PASSED_ESC: escapeHtml(st.passed ?? "N/A"),
        ST_FAILED_CLASS: Number(st.failed) > 0 ? "text-red-500" : "text-emerald-600",
        ST_FAILED_ESC: escapeHtml(st.failed ?? "N/A"),
        SELF_TEST_CHECKS_GRID: selfTestChecksGrid,
        SELF_TEST_JSON_BOX: renderJsonBox(selfTest.data),
        METRICS_OK_CLASS: metrics.ok ? "text-emerald-600" : "text-red-500",
        METRICS_HTTP: metrics.status,
        AI_TOTAL_ESC: escapeHtml(aiMetrics.total_requests ?? "N/A"),
        AI_FB_CLASS: Number(aiMetrics.fallback_rate) > 0.5 ? "text-orange-500" : "text-emerald-600",
        AI_FB_ESC: escapeHtml(aiMetrics.fallback_rate ?? "N/A"),
        GEMINI_FLASH_ESC: escapeHtml(modelUsage["gemini-2.5-flash"] ?? 0),
        TMPL_FB_ESC: escapeHtml(modelUsage.template_after_gemini_error ?? 0),
        QUOTA_ESC: escapeHtml(aiMetrics.quota_exceeded_count ?? 0),
        CACHE_HIT_ESC: escapeHtml(aiMetrics.cache_hit_rate ?? "N/A"),
        METRICS_JSON_BOX: renderJsonBox(metrics.data),
        DQ_OK_CLASS: dataQuality.ok ? "text-emerald-600" : "text-red-500",
        DQ_HTTP: dataQuality.status,
        DQ_ISSUES_ESC: escapeHtml(dqScan.issue_count ?? "N/A"),
        DQ_HIGH_ESC: escapeHtml(dqScan.severity_counts?.high ?? "N/A"),
        DQ_MED_ESC: escapeHtml(dqScan.severity_counts?.medium ?? "N/A"),
        DQ_LOW_ESC: escapeHtml(dqScan.severity_counts?.low ?? "N/A"),
        DQ_AUTOFIX_ESC: escapeHtml(dqAutofix.changed_count ?? "N/A"),
        DQ_REV_CLASS: dqReviewed.exists ? "text-emerald-600" : "text-red-500",
        DQ_REV_ESC: escapeHtml(dqReviewed.exists ?? "N/A"),
        DQ_ISSUE_TYPES_GRID: dqIssueTypesGrid,
        DQ_JSON_BOX: renderJsonBox(dataQuality.data),
        SCRIPT_NONCE_ATTR: scriptNonceAttr(cspNonce)
      });

      res.send(renderLayout(content, "rag-ai", "RAG AI", cspNonce));
    } catch (error) {
      res.status(500).send("RAG AI Dashboard Error: " + error.message);
    }
  });
    // 6. RAG AI Actions
  router.post("/rag-ai/reload-place-store", async (req, res) => {
    const result = await postRagJson("/admin/rag/place-store/reload");
    res.status(result.ok ? 200 : 502).json(result);
  });

  router.post("/rag-ai/clear-cache", async (req, res) => {
    const result = await postRagJson("/admin/cache/clear");
    res.status(result.ok ? 200 : 502).json(result);
  });
    router.get("/rag-ai/data-quality-issues", async (req, res) => {
    const result = await fetchRagJson("/admin/data-quality/issues", 5000);
    res.status(result.ok ? 200 : 502).json(result);
  });

  router.get("/rag-ai/ai-metrics", async (req, res) => {
    const result = await fetchRagJson("/admin/ai/metrics", 5000);
    res.status(result.ok ? 200 : 502).json(result);
  });
  router.get("/rag-ai/ai-logs", async (req, res) => {
  const result = await fetchRagJson("/admin/ai/logs", 5000);
  res.status(result.ok ? 200 : 502).json(result);
});
  router.post("/rag-ai/debug-query", async (req, res) => {
  const message = String(req.body?.message || req.body?.query || "").trim();

  if (!message) {
    return res.status(400).json({
      ok: false,
      status: 400,
      data: {
        error: "Thiếu message"
      }
    });
  }

  const result = await postRagJson(
    "/admin/ai/debug-query",
    { message },
    RAG_ADMIN_DEBUG_TIMEOUT_MS,
  );
  res.status(result.ok ? 200 : 502).json(result);
});
}
