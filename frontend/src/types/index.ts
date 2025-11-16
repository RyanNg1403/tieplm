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
export type SSEEventType = 'token' | 'sources' | 'done' | 'error' | 'progress' | 'validation';

export interface SSEEvent {
  type: SSEEventType;
  content?: string;
  sources?: SourceReference[];
  session_id?: string;
  progress?: number;
  quiz_id?: string;
  result?: QuizValidationResult;
  total_questions?: number;
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

// ============================================================================
// Quiz Types (Non-conversational, dedicated tables)
// ============================================================================

// Quiz metadata
export interface Quiz {
  id: string;
  user_id: string;
  topic?: string;
  chapters?: string[];
  question_type: 'mcq' | 'open_ended' | 'mixed';
  num_questions: number;
  created_at: string;
  questions: QuizQuestion[];
}

// Individual quiz question
export interface QuizQuestion {
  id: number;
  quiz_id: string;
  question_index: number;
  question: string;
  question_type: 'mcq' | 'open_ended';

  // MCQ fields
  options?: {
    A: string;
    B: string;
    C: string;
    D: string;
  };
  correct_answer?: string; // "A", "B", "C", "D"

  // Open-ended fields
  reference_answer?: string;
  key_points?: string[];

  // Common fields
  explanation?: string;

  // Video source fields
  source_index?: number;
  video_id?: string;
  video_title?: string;
  video_url?: string;
  timestamp?: number; // in seconds

  created_at: string;
}

// Validation result for a single question
export interface QuizValidationResult {
  question_index: number;
  question_type: 'mcq' | 'open_ended';
  user_answer: string;

  // MCQ validation
  is_correct?: boolean;
  correct_answer?: string;

  // Open-ended validation
  llm_score?: number; // 0-100
  llm_feedback?: {
    score: number;
    feedback: string;
    covered_points: string[];
    missing_points: string[];
  };

  // Common fields
  explanation?: string;

  // Video source
  video_id?: string;
  video_title?: string;
  video_url?: string;
  timestamp?: number;
}

// Request models
export interface GenerateQuizRequest {
  video_ids?: string[];
  query?: string;
  chapters?: string[];
  question_type: 'mcq' | 'open_ended' | 'mixed';
  num_questions?: number;
}

export interface ValidateAnswerItem {
  question_index: number;
  answer: string; // For MCQ: "A", "B", "C", "D"; For open-ended: full text
}

export interface ValidateAnswersRequest {
  quiz_id: string;
  answers: ValidateAnswerItem[];
}
