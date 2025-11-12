// API Response Types

export interface Source {
  video_url: string;
  video_id: string;
  chapter: string;
  timestamp: string;
  timestamp_seconds: number;
}

export interface QuestionResponse {
  answer: string;
  sources: Source[];
  session_id: string;
}

export interface SummaryResponse {
  summary: string;
  sources: Source[];
}

export interface QuizQuestion {
  question_id: number;
  question: string;
  options?: string[];  // For MCQ
  timestamp: string;
  video_url: string;
}

export interface QuizResponse {
  quiz_id: number;
  questions: QuizQuestion[];
}

export interface QuizValidationResponse {
  score: number;
  total: number;
  results: Record<number, {
    correct: boolean;
    user_answer: string;
    correct_answer: string;
  }>;
}

export type TaskType = 'qa' | 'text_summary' | 'video_summary' | 'quiz';

