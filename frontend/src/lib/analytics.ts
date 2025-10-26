/**
 * Analytics API client functions
 */

import apiClient from "./api-client";

export interface IntentsCount {
  [intent: string]: number;
}

export interface ReviewRate {
  total: number;
  approved: number;
  rejected: number;
  editing: number;
  pending: number;
  approved_rate: number;
  rejected_rate: number;
  editing_rate: number;
  pending_rate: number;
}

export interface FRTMetrics {
  avg_seconds: number;
  median_seconds: number;
  min_seconds: number;
  max_seconds: number;
  sla_threshold_seconds: number;
  sla_met_count: number;
  sla_met_percentage: number;
  total_with_frt: number;
}

export interface AnalyticsMetrics {
  intents_count: IntentsCount;
  review_rate: ReviewRate;
  frt: FRTMetrics;
}

export interface AnalyticsTrend {
  intents_count_previous: IntentsCount;
  review_rate_previous: ReviewRate;
  frt_previous: FRTMetrics;
}

export interface AnalyticsSummary {
  window: "7d" | "30d";
  workspace_id: string | null;
  period_start: string;
  period_end: string;
  metrics: AnalyticsMetrics;
  trend: AnalyticsTrend;
}

export interface GetAnalyticsSummaryParams {
  window?: "7d" | "30d";
  workspace_id?: string;
  sla_threshold_seconds?: number;
}

/**
 * Get analytics summary for the specified time window
 * @param params Query parameters
 * @returns Analytics summary with metrics and trends
 */
export async function getAnalyticsSummary(
  params?: GetAnalyticsSummaryParams
): Promise<AnalyticsSummary> {
  const response = await apiClient.get<AnalyticsSummary>("/analytics/summary", {
    params: {
      window: params?.window || "7d",
      workspace_id: params?.workspace_id,
      sla_threshold_seconds: params?.sla_threshold_seconds,
    },
  });
  return response.data;
}

/**
 * Format seconds into human-readable time string
 * @param seconds Number of seconds
 * @returns Formatted string (e.g., "2m 30s")
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  if (remainingSeconds === 0) {
    return `${minutes}m`;
  }
  return `${minutes}m ${remainingSeconds}s`;
}

/**
 * Calculate percentage change between current and previous values
 * @param current Current value
 * @param previous Previous value
 * @returns Percentage change (positive = increase, negative = decrease)
 */
export function calculatePercentageChange(
  current: number,
  previous: number
): number {
  if (previous === 0) {
    return current > 0 ? 100 : 0;
  }
  return ((current - previous) / previous) * 100;
}

/**
 * Format percentage with optional decimal places
 * @param value Percentage value
 * @param decimals Number of decimal places (default: 1)
 * @returns Formatted percentage string
 */
export function formatPercentage(value: number, decimals: number = 1): string {
  return `${value.toFixed(decimals)}%`;
}
