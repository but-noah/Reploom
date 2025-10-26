import { apiClient } from "./api-client";

export interface DraftReview {
  id: string;
  thread_id: string;
  draft_html: string;
  original_message_summary: string;
  original_message_excerpt: string | null;
  intent: string | null;
  confidence: number | null;
  violations: string[];
  status: "pending" | "approved" | "rejected" | "editing";
  feedback: string | null;
  edit_notes: string | null;
  draft_version: number;
  created_at: string;
  updated_at: string;
  reviewed_at: string | null;
}

export interface CreateReviewRequest {
  thread_id: string;
  draft_html: string;
  original_message_summary: string;
  original_message_excerpt?: string;
  intent?: string;
  confidence?: number;
  violations?: string[];
  run_id?: string;
  workspace_id?: string;
}

export interface UpdateReviewRequest {
  draft_html: string;
  edit_notes?: string;
}

export interface ReviewActionRequest {
  feedback?: string;
}

export async function createReview(
  data: CreateReviewRequest
): Promise<DraftReview> {
  const response = await apiClient.post("/api/agents/reploom/reviews", data);
  return response.data;
}

export async function listReviews(params?: {
  status?: string;
  intent?: string;
}): Promise<DraftReview[]> {
  const response = await apiClient.get("/api/agents/reploom/reviews", {
    params,
  });
  return response.data;
}

export async function getReview(reviewId: string): Promise<DraftReview> {
  const response = await apiClient.get(
    `/api/agents/reploom/reviews/${reviewId}`
  );
  return response.data;
}

export async function approveReview(
  reviewId: string,
  data?: ReviewActionRequest
): Promise<DraftReview> {
  const response = await apiClient.post(
    `/api/agents/reploom/reviews/${reviewId}/approve`,
    data || {}
  );
  return response.data;
}

export async function rejectReview(
  reviewId: string,
  data?: ReviewActionRequest
): Promise<DraftReview> {
  const response = await apiClient.post(
    `/api/agents/reploom/reviews/${reviewId}/reject`,
    data || {}
  );
  return response.data;
}

export async function requestEdit(
  reviewId: string,
  data: UpdateReviewRequest
): Promise<DraftReview> {
  const response = await apiClient.post(
    `/api/agents/reploom/reviews/${reviewId}/request-edit`,
    data
  );
  return response.data;
}

export async function runDraft(data: {
  thread_id?: string;
  message_excerpt: string;
  workspace_id?: string;
}): Promise<{
  draft_html: string | null;
  confidence: number | null;
  intent: string | null;
  violations: string[];
  thread_id: string;
  run_id: string;
}> {
  const response = await apiClient.post("/api/agents/reploom/run-draft", data);
  return response.data;
}
