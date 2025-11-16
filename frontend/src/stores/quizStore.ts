/**
 * Zustand store for quiz state management
 *
 * Quiz is NON-CONVERSATIONAL:
 * - Generate quiz once
 * - Answer questions
 * - Submit for validation
 * - No chat sessions/messages
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Quiz, QuizValidationResult } from '../types';

interface QuizStore {
  // Current quiz
  currentQuiz: Quiz | null;
  setCurrentQuiz: (quiz: Quiz | null) => void;

  // Persisted quiz ID (for restoration after refresh)
  persistedQuizId: string | null;
  setPersistedQuizId: (id: string | null) => void;

  // Quiz generation state
  isGenerating: boolean;
  setIsGenerating: (generating: boolean) => void;
  generationProgress: number;
  setGenerationProgress: (progress: number) => void;

  // User answers (question_index -> answer)
  userAnswers: Map<number, string>;
  setAnswer: (questionIndex: number, answer: string) => void;
  clearAnswers: () => void;

  // Validation state
  isValidating: boolean;
  setIsValidating: (validating: boolean) => void;
  validationResults: Map<number, QuizValidationResult>;
  addValidationResult: (result: QuizValidationResult) => void;
  clearValidationResults: () => void;

  // Quiz history (for left sidebar)
  quizHistory: Array<{
    id: string;
    topic?: string;
    question_type: string;
    num_questions: number;
    created_at: string;
  }>;
  setQuizHistory: (history: Array<{
    id: string;
    topic?: string;
    question_type: string;
    num_questions: number;
    created_at: string;
  }>) => void;

  // Chapter filter (for quiz generation)
  selectedChapters: string[];
  setSelectedChapters: (chapters: string[]) => void;

  // Reset quiz state (when switching tasks or starting new quiz)
  resetQuiz: () => void;

  // Reset all state
  reset: () => void;
}

export const useQuizStore = create<QuizStore>()(
  persist(
    (set) => ({
      // Initial state
      currentQuiz: null,
      persistedQuizId: null,
      isGenerating: false,
      generationProgress: 0,
      userAnswers: new Map(),
      isValidating: false,
      validationResults: new Map(),
      quizHistory: [],
      selectedChapters: [],

      // Actions
      setCurrentQuiz: (quiz) => set({
        currentQuiz: quiz,
        persistedQuizId: quiz?.id || null,
      }),

      setPersistedQuizId: (id) => set({ persistedQuizId: id }),

      setIsGenerating: (generating) => set({ isGenerating: generating }),

      setGenerationProgress: (progress) => set({ generationProgress: progress }),

      setAnswer: (questionIndex, answer) => set((state) => {
        const newAnswers = new Map(state.userAnswers);
        newAnswers.set(questionIndex, answer);
        return { userAnswers: newAnswers };
      }),

      clearAnswers: () => set({ userAnswers: new Map() }),

      setIsValidating: (validating) => set({ isValidating: validating }),

      addValidationResult: (result) => set((state) => {
        const newResults = new Map(state.validationResults);
        newResults.set(result.question_index, result);
        return { validationResults: newResults };
      }),

      clearValidationResults: () => set({ validationResults: new Map() }),

      setQuizHistory: (history) => set({ quizHistory: history }),

      setSelectedChapters: (chapters) => set({ selectedChapters: chapters }),

      resetQuiz: () => set({
        currentQuiz: null,
        persistedQuizId: null,
        isGenerating: false,
        generationProgress: 0,
        userAnswers: new Map(),
        isValidating: false,
        validationResults: new Map(),
      }),

      reset: () => set({
        currentQuiz: null,
        persistedQuizId: null,
        isGenerating: false,
        generationProgress: 0,
        userAnswers: new Map(),
        isValidating: false,
        validationResults: new Map(),
        quizHistory: [],
        selectedChapters: [],
      })
    }),
    {
      name: 'quiz-storage',
      // Only persist quiz ID (not the full quiz object)
      partialize: (state) => ({
        persistedQuizId: state.persistedQuizId,
      }),
    }
  )
);
