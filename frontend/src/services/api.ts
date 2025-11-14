/**
 * API service for backend communication
 */
import axios from 'axios';
import { ChatSession, ChatMessage } from '../types';

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
