/**
 * Admin section router: AI report.
 *
 * Phase 4 split — handler body is a byte-identical copy of the original
 * `router.get("/ai-report", …)` block in the old `src/admin.js`. The RAG
 * fetch helper `postRagJson` is now imported from `./_shared/ragHttp.js`.
 */

import { getResolvedAiModelUrl } from "../config/env.js";
import * as appPlacesStatsRepository from "../repositories/appPlacesStats.repository.js";
import { postRagJson } from "./_shared/ragHttp.js";

export function registerAiReportAdminRoutes(router) {
  // 5. AI Report API
  router.get("/ai-report", async (req, res) => {
    try {
      const catStats = await appPlacesStatsRepository.getCategoryCounts();
      const overall = await appPlacesStatsRepository.getOverallRatingAverage();
      const avgNum = Number(overall?.avgRating);
      const avgRatingText = Number.isFinite(avgNum) ? avgNum.toFixed(2) : "0.00";

      const prompt = `Phân tích dữ liệu ứng dụng UnuTrip:
        - Thống kê danh mục địa điểm: ${JSON.stringify(catStats)}
        - Điểm đánh giá trung bình: ${avgRatingText}
        Hãy viết báo cáo ngắn gọn gồm 3 mục:
        1. Nhận xét chất lượng dữ liệu hiện tại.
        2. Điểm mạnh của hệ thống gợi ý du lịch.
        3. Đề xuất cải thiện nội dung và trải nghiệm người dùng.`;

      let report = "";
      const aiUrl = getResolvedAiModelUrl();

      if (aiUrl) {
        try {
          const aiRes = await fetch(aiUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: prompt })
          });
          const aiData = await aiRes.json();
          report = typeof aiData.answer === "string" ? aiData.answer : "";
        } catch (err) {
          console.warn("Admin AI report: local AI failed, using RAG:", err.message);
        }
      }

      if (!report?.trim()) {
        const result = await postRagJson(
          "/rag/chat",
          { message: prompt, top_k: 6, mode: "balanced", include_prompt: false },
          30000
        );
        if (!result.ok) {
          return res.json({
            success: false,
            message: result.data?.detail || result.data?.error || "RAG không khả dụng"
          });
        }
        report = result.data?.answer ?? "";
      }

      if (!report) {
        return res.json({ success: false, message: "Không tạo được báo cáo (rỗng)." });
      }

      return res.json({ success: true, report });
    } catch (error) { res.json({ success: false, message: error.message }); }
  });
}
