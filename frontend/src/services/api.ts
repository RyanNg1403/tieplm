import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Q&A API
export const askQuestion = async (question: string, sessionId?: string) => {
  const response = await apiClient.post('/qa/ask', { question, session_id: sessionId });
  return response.data;
};

// Text Summarization API
export const summarizeTopic = async (topic: string, chapterFilter?: string) => {
  const response = await apiClient.post('/text-summary/summarize', {
    topic,
    chapter_filter: chapterFilter,
  });
  return response.data;
};

// Video Summarization API
export const summarizeVideo = async (videoId: string) => {
  const response = await apiClient.post('/video-summary/summarize', { video_id: videoId });
  return response.data;
};

export const listVideos = async () => {
  const response = await apiClient.get('/video-summary/videos');
  return response.data;
};

// Quiz API
export const generateQuiz = async (videoId: string, questionType: string, numQuestions: number = 5) => {
  const response = await apiClient.post('/quiz/generate', {
    video_id: videoId,
    question_type: questionType,
    num_questions: numQuestions,
  });
  return response.data;
};

export const validateQuiz = async (quizId: number, answers: Record<string, string>) => {
  const response = await apiClient.post('/quiz/validate', {
    quiz_id: quizId,
    answers,
  });
  return response.data;
};

export default apiClient;

