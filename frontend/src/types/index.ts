/**
 * Type definitions for the frontend application
 */

// Task types
export type TaskType = 'text_summary' | 'qa' | 'video_summary' | 'quiz';

// Chat session
export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

// Message role
export type MessageRole = 'user' | 'assistant';

// Source reference (for citations)
export interface SourceReference {
  index: number;
  video_id: string;
  chapter: string;
  video_title: string;
  video_url: string;
  start_time: number;
  end_time: number;
  text: string;
  score?: number;
}

// Chat message
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  sources?: SourceReference[];
  created_at: string;
}

// SSE Event types
export type SSEEventType = 'token' | 'sources' | 'done' | 'error' | 'progress';

export interface SSEEvent {
  type: SSEEventType;
  content?: string;
  sources?: SourceReference[];
  session_id?: string;
  progress?: number;
}

// API Request/Response types
export interface SummarizeRequest {
  query: string;
  chapters?: string[];
  session_id?: string;
}

export interface FollowupRequest {
  query: string;
  chapters?: string[];
}
