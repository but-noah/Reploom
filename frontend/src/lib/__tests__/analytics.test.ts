import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getAnalyticsSummary,
  formatDuration,
  calculatePercentageChange,
  formatPercentage,
  type AnalyticsSummary,
} from "../analytics";
import { apiClient } from "../api-client";

vi.mock("../api-client");

describe("Analytics API Functions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getAnalyticsSummary", () => {
    it("should fetch analytics summary with default parameters", async () => {
      const mockResponse: AnalyticsSummary = {
        window: "7d",
        workspace_id: null,
        period_start: "2025-10-19T00:00:00Z",
        period_end: "2025-10-26T00:00:00Z",
        metrics: {
          intents_count: { support: 10, cs: 5 },
          review_rate: {
            total: 15,
            approved: 10,
            rejected: 3,
            editing: 1,
            pending: 1,
            approved_rate: 66.67,
            rejected_rate: 20.0,
            editing_rate: 6.67,
            pending_rate: 6.67,
          },
          frt: {
            avg_seconds: 150.5,
            median_seconds: 120.0,
            min_seconds: 60.0,
            max_seconds: 300.0,
            sla_threshold_seconds: 300,
            sla_met_count: 12,
            sla_met_percentage: 85.71,
            total_with_frt: 14,
          },
        },
        trend: {
          intents_count_previous: { support: 8, cs: 4 },
          review_rate_previous: {
            total: 12,
            approved: 8,
            rejected: 2,
            editing: 1,
            pending: 1,
            approved_rate: 66.67,
            rejected_rate: 16.67,
            editing_rate: 8.33,
            pending_rate: 8.33,
          },
          frt_previous: {
            avg_seconds: 180.0,
            median_seconds: 150.0,
            min_seconds: 80.0,
            max_seconds: 350.0,
            sla_threshold_seconds: 300,
            sla_met_count: 10,
            sla_met_percentage: 83.33,
            total_with_frt: 12,
          },
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      const result = await getAnalyticsSummary();

      expect(apiClient.get).toHaveBeenCalledWith("/analytics/summary", {
        params: {
          window: "7d",
          workspace_id: undefined,
          sla_threshold_seconds: undefined,
        },
      });
      expect(result).toEqual(mockResponse);
    });

    it("should fetch analytics summary with custom parameters", async () => {
      const mockResponse: AnalyticsSummary = {
        window: "30d",
        workspace_id: "ws-123",
        period_start: "2025-09-26T00:00:00Z",
        period_end: "2025-10-26T00:00:00Z",
        metrics: {
          intents_count: { support: 50, cs: 30, exec: 20 },
          review_rate: {
            total: 100,
            approved: 70,
            rejected: 20,
            editing: 5,
            pending: 5,
            approved_rate: 70.0,
            rejected_rate: 20.0,
            editing_rate: 5.0,
            pending_rate: 5.0,
          },
          frt: {
            avg_seconds: 200.0,
            median_seconds: 180.0,
            min_seconds: 30.0,
            max_seconds: 600.0,
            sla_threshold_seconds: 180,
            sla_met_count: 60,
            sla_met_percentage: 63.16,
            total_with_frt: 95,
          },
        },
        trend: {
          intents_count_previous: { support: 45, cs: 25, exec: 18 },
          review_rate_previous: {
            total: 88,
            approved: 60,
            rejected: 18,
            editing: 5,
            pending: 5,
            approved_rate: 68.18,
            rejected_rate: 20.45,
            editing_rate: 5.68,
            pending_rate: 5.68,
          },
          frt_previous: {
            avg_seconds: 220.0,
            median_seconds: 200.0,
            min_seconds: 40.0,
            max_seconds: 650.0,
            sla_threshold_seconds: 180,
            sla_met_count: 50,
            sla_met_percentage: 58.14,
            total_with_frt: 86,
          },
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      const result = await getAnalyticsSummary({
        window: "30d",
        workspace_id: "ws-123",
        sla_threshold_seconds: 180,
      });

      expect(apiClient.get).toHaveBeenCalledWith("/analytics/summary", {
        params: {
          window: "30d",
          workspace_id: "ws-123",
          sla_threshold_seconds: 180,
        },
      });
      expect(result).toEqual(mockResponse);
    });

    it("should handle API errors", async () => {
      const error = new Error("Network error");
      vi.mocked(apiClient.get).mockRejectedValue(error);

      await expect(getAnalyticsSummary()).rejects.toThrow("Network error");
    });
  });

  describe("formatDuration", () => {
    it("should format seconds less than 60", () => {
      expect(formatDuration(30)).toBe("30s");
      expect(formatDuration(45.7)).toBe("46s");
      expect(formatDuration(0)).toBe("0s");
    });

    it("should format minutes without seconds", () => {
      expect(formatDuration(60)).toBe("1m");
      expect(formatDuration(120)).toBe("2m");
      expect(formatDuration(300)).toBe("5m");
    });

    it("should format minutes with seconds", () => {
      expect(formatDuration(90)).toBe("1m 30s");
      expect(formatDuration(125)).toBe("2m 5s");
      expect(formatDuration(185)).toBe("3m 5s");
    });

    it("should round seconds properly", () => {
      expect(formatDuration(90.4)).toBe("1m 30s");
      expect(formatDuration(90.6)).toBe("1m 31s");
    });
  });

  describe("calculatePercentageChange", () => {
    it("should calculate positive percentage change", () => {
      expect(calculatePercentageChange(120, 100)).toBe(20);
      expect(calculatePercentageChange(150, 100)).toBe(50);
    });

    it("should calculate negative percentage change", () => {
      expect(calculatePercentageChange(80, 100)).toBe(-20);
      expect(calculatePercentageChange(50, 100)).toBe(-50);
    });

    it("should handle zero previous value", () => {
      expect(calculatePercentageChange(100, 0)).toBe(100);
      expect(calculatePercentageChange(0, 0)).toBe(0);
    });

    it("should handle zero current value", () => {
      expect(calculatePercentageChange(0, 100)).toBe(-100);
    });

    it("should handle same values", () => {
      expect(calculatePercentageChange(100, 100)).toBe(0);
    });

    it("should calculate decimal percentages", () => {
      expect(calculatePercentageChange(105, 100)).toBe(5);
      expect(calculatePercentageChange(95, 100)).toBe(-5);
    });
  });

  describe("formatPercentage", () => {
    it("should format percentage with default decimal places", () => {
      expect(formatPercentage(50.0)).toBe("50.0%");
      expect(formatPercentage(66.67)).toBe("66.7%");
      expect(formatPercentage(33.33)).toBe("33.3%");
    });

    it("should format percentage with custom decimal places", () => {
      expect(formatPercentage(50.0, 0)).toBe("50%");
      expect(formatPercentage(66.666, 2)).toBe("66.67%");
      expect(formatPercentage(33.333, 3)).toBe("33.333%");
    });

    it("should handle zero percentage", () => {
      expect(formatPercentage(0)).toBe("0.0%");
      expect(formatPercentage(0, 0)).toBe("0%");
    });

    it("should handle 100 percentage", () => {
      expect(formatPercentage(100)).toBe("100.0%");
      expect(formatPercentage(100, 2)).toBe("100.00%");
    });

    it("should round properly", () => {
      expect(formatPercentage(50.14, 1)).toBe("50.1%");
      expect(formatPercentage(50.15, 1)).toBe("50.2%");
      expect(formatPercentage(50.16, 1)).toBe("50.2%");
    });
  });
});
