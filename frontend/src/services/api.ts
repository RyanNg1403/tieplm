/**
 * API service for backend communication
 */
import axios from 'axios';
import {
  ChatSession,
  ChatMessage,
  QuizQuestion,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json; charset=utf-8',
  },
  responseType: 'json',
});

// ============================================================================
// Universal Session API (used by all tasks)
// ============================================================================

export const sessionsAPI = {
  /**
   * Get all sessions for a user, optionally filtered by task type
   */
  getSessions: async (
    userId: string = 'default_user',
    taskType?: string
  ): Promise<ChatSession[]> => {
    const response = await apiClient.get<ChatSession[]>('/api/sessions', {
      params: {
        user_id: userId,
        ...(taskType && { task_type: taskType })
      }
    });
    return response.data;
  },

  /**
   * Get messages in a session
   */
  getSessionMessages: async (sessionId: string): Promise<ChatMessage[]> => {
    const response = await apiClient.get<ChatMessage[]>(
      `/api/sessions/${sessionId}/messages`
    );
    return response.data;
  },

  /**
   * Delete a session
   */
  deleteSession: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/api/sessions/${sessionId}`);
  },
};

// ============================================================================
// Text Summary API (task-specific endpoints)
// ============================================================================

export const textSummaryAPI = {
  /**
   * Get SSE stream URL for summarization
   */
  getSummarizeStreamURL: (): string => {
    return `${API_BASE_URL}/api/text-summary/summarize`;
  },

  /**
   * Get SSE stream URL for followup
   */
  getFollowupStreamURL: (sessionId: string): string => {
    return `${API_BASE_URL}/api/text-summary/sessions/${sessionId}/followup`;
  },
};

// ============================================================================
// Q&A API (task-specific endpoints)
// ============================================================================

export const qaAPI = {
  /**
   * Get SSE stream URL for Q&A
   */
  getAskStreamURL: (): string => {
    return `${API_BASE_URL}/api/qa/ask`;
  },

  /**
   * Get SSE stream URL for followup
   */
  getFollowupStreamURL: (sessionId: string): string => {
    return `${API_BASE_URL}/api/qa/sessions/${sessionId}/followup`;
  },
};

// ============================================================================
// Video Summary API (task-specific endpoints)
// ============================================================================

export interface VideoInfo {
  id: string;
  chapter: string;
  title: string;
  url: string;
  duration: number;
}

export interface VideoSummaryResponse {
  video_id: string;
  summary: string;
  sources: any[];
  has_summary: boolean;
  created_at?: string;
  updated_at?: string;
}

export const videoSummaryAPI = {
  /**
   * Get SSE stream URL for video summarization
   */
  getSummarizeStreamURL: (): string => {
    return `${API_BASE_URL}/api/video-summary/summarize`;
  },

  /**
   * Get list of all available videos
   */
  getVideos: async (): Promise<VideoInfo[]> => {
    const response = await apiClient.get<VideoInfo[]>('/api/video-summary/videos');
    return response.data;
  },

  /**
   * Get info for a specific video
   */
  getVideoInfo: async (videoId: string): Promise<VideoInfo> => {
    const encoded = encodeURIComponent(videoId);
    const response = await apiClient.get<VideoInfo>(`/api/video-summary/videos/${encoded}`);
    return response.data;
  },

  /**
   * Get existing pre-computed summary for a video (non-streaming)
   */
  getVideoSummary: async (videoId: string): Promise<VideoSummaryResponse> => {
    const encoded = encodeURIComponent(videoId);
    const response = await apiClient.get<VideoSummaryResponse>(`/api/video-summary/summary/${encoded}`);
    return response.data;
  },
};

// ============================================================================
// Quiz API (task-specific endpoints)
// ============================================================================

export interface QuizHistory {
  id: string;
  topic?: string;
  chapters?: string[];
  question_type: string;
  num_questions: number;
  created_at: string;
}

export const quizAPI = {
  /**
   * Get SSE stream URL for quiz generation
   * POST /api/quiz/generate with GenerateQuizRequest body
   * Returns SSE stream with progress and quiz_id
   */
  getGenerateStreamURL: (): string => {
    return `${API_BASE_URL}/api/quiz/generate`;
  },

  /**
   * Get SSE stream URL for answer validation
   * POST /api/quiz/validate with ValidateAnswersRequest body
   * Returns SSE stream with incremental validation results
   */
  getValidateStreamURL: (): string => {
    return `${API_BASE_URL}/api/quiz/validate`;
  },

  /**
   * Get a specific quiz by ID (non-streaming)
   * GET /api/quiz/{quiz_id}
   */
  getQuiz: async (quizId: string): Promise<{ quiz_id: string; questions: QuizQuestion[] }> => {
    const response = await apiClient.get(`/api/quiz/${quizId}`);
    return response.data;
  },

  /**
   * Get quiz history for a user
   * GET /api/quiz/history
   */
  getQuizHistory: async (userId: string = 'default_user'): Promise<QuizHistory[]> => {
    const response = await apiClient.get<QuizHistory[]>('/api/quiz/history', {
      params: { user_id: userId }
    });
    return response.data;
  },

  /**
   * Delete a quiz by ID
   * DELETE /api/quiz/{quiz_id}
   */
  deleteQuiz: async (quizId: string): Promise<void> => {
    await apiClient.delete(`/api/quiz/${quizId}`);
  },

  /**
   * Get previous attempts for a quiz
   * GET /api/quiz/{quiz_id}/attempts
   */
  getQuizAttempts: async (quizId: string): Promise<Array<{
    question_id: number;
    user_answer: string;
    is_correct?: boolean;
    llm_score?: number;
    llm_feedback?: any;
    submitted_at?: string;
  }>> => {
    const response = await apiClient.get(`/api/quiz/${quizId}/attempts`);
    return response.data;
  },
};

// ============================================================================
// Chapters API (for filter)
// ============================================================================

export const chaptersAPI = {
  /**
   * Get available chapters (hardcoded based on chapters_urls.json ground truth)
   *
   * Note: Chapters are static course content (Chương 2-9) and won't change.
   * No need for API call - this is the single source of truth.
   */
  getChapters: (): string[] => {
    return [
      'Chương 2',
      'Chương 3',
      'Chương 4',
      'Chương 5',
      'Chương 6',
      'Chương 7',
      'Chương 8',
      'Chương 9',
    ];
  },
};
