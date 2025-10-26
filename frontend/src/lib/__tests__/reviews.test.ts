/**
 * Tests for review API functions
 *
 * Note: To run these tests, install vitest and @testing-library/react:
 * npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
 *
 * Add to package.json scripts:
 * "test": "vitest"
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { apiClient } from '../api-client';
import {
  createReview,
  listReviews,
  getReview,
  approveReview,
  rejectReview,
  requestEdit,
  runDraft,
} from '../reviews';

// Mock axios
vi.mock('../api-client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('Review API Functions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('createReview', () => {
    it('should create a new review', async () => {
      const mockReview = {
        id: '123',
        thread_id: 'thread-1',
        draft_html: '<p>Test draft</p>',
        original_message_summary: 'Test summary',
        original_message_excerpt: 'Test excerpt',
        intent: 'support',
        confidence: 0.95,
        violations: [],
        status: 'pending',
        feedback: null,
        edit_notes: null,
        draft_version: 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        reviewed_at: null,
      };

      vi.mocked(apiClient.post).mockResolvedValue({ data: mockReview });

      const result = await createReview({
        thread_id: 'thread-1',
        draft_html: '<p>Test draft</p>',
        original_message_summary: 'Test summary',
      });

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/agents/reploom/reviews',
        expect.any(Object)
      );
      expect(result).toEqual(mockReview);
    });
  });

  describe('listReviews', () => {
    it('should list all reviews', async () => {
      const mockReviews = [
        {
          id: '123',
          thread_id: 'thread-1',
          status: 'pending',
        },
      ];

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockReviews });

      const result = await listReviews();

      expect(apiClient.get).toHaveBeenCalledWith(
        '/api/agents/reploom/reviews',
        { params: undefined }
      );
      expect(result).toEqual(mockReviews);
    });

    it('should filter reviews by status', async () => {
      const mockReviews = [
        {
          id: '123',
          thread_id: 'thread-1',
          status: 'pending',
        },
      ];

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockReviews });

      const result = await listReviews({ status: 'pending' });

      expect(apiClient.get).toHaveBeenCalledWith(
        '/api/agents/reploom/reviews',
        { params: { status: 'pending' } }
      );
      expect(result).toEqual(mockReviews);
    });
  });

  describe('getReview', () => {
    it('should get a specific review', async () => {
      const mockReview = {
        id: '123',
        thread_id: 'thread-1',
        status: 'pending',
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockReview });

      const result = await getReview('123');

      expect(apiClient.get).toHaveBeenCalledWith(
        '/api/agents/reploom/reviews/123'
      );
      expect(result).toEqual(mockReview);
    });
  });

  describe('approveReview', () => {
    it('should approve a review', async () => {
      const mockReview = {
        id: '123',
        status: 'approved',
      };

      vi.mocked(apiClient.post).mockResolvedValue({ data: mockReview });

      const result = await approveReview('123');

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/agents/reploom/reviews/123/approve',
        {}
      );
      expect(result).toEqual(mockReview);
    });

    it('should approve a review with feedback', async () => {
      const mockReview = {
        id: '123',
        status: 'approved',
        feedback: 'Looks good!',
      };

      vi.mocked(apiClient.post).mockResolvedValue({ data: mockReview });

      const result = await approveReview('123', { feedback: 'Looks good!' });

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/agents/reploom/reviews/123/approve',
        { feedback: 'Looks good!' }
      );
      expect(result).toEqual(mockReview);
    });
  });

  describe('rejectReview', () => {
    it('should reject a review', async () => {
      const mockReview = {
        id: '123',
        status: 'rejected',
        feedback: 'Not appropriate',
      };

      vi.mocked(apiClient.post).mockResolvedValue({ data: mockReview });

      const result = await rejectReview('123', { feedback: 'Not appropriate' });

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/agents/reploom/reviews/123/reject',
        { feedback: 'Not appropriate' }
      );
      expect(result).toEqual(mockReview);
    });
  });

  describe('requestEdit', () => {
    it('should request edit for a review', async () => {
      const mockReview = {
        id: '123',
        status: 'editing',
        draft_html: '<p>Updated draft</p>',
        draft_version: 2,
      };

      vi.mocked(apiClient.post).mockResolvedValue({ data: mockReview });

      const result = await requestEdit('123', {
        draft_html: '<p>Updated draft</p>',
        edit_notes: 'Fixed typo',
      });

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/agents/reploom/reviews/123/request-edit',
        {
          draft_html: '<p>Updated draft</p>',
          edit_notes: 'Fixed typo',
        }
      );
      expect(result).toEqual(mockReview);
    });
  });

  describe('runDraft', () => {
    it('should run draft generation', async () => {
      const mockResponse = {
        draft_html: '<p>Generated draft</p>',
        confidence: 0.85,
        intent: 'support',
        violations: [],
        thread_id: 'thread-1',
        run_id: 'run-1',
      };

      vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

      const result = await runDraft({
        message_excerpt: 'Customer needs help',
      });

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/agents/reploom/run-draft',
        expect.any(Object)
      );
      expect(result).toEqual(mockResponse);
    });
  });
});
