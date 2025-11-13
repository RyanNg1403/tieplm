/**
 * Zustand store for chat state management
 */
import { create } from 'zustand';
import { TaskType, ChatSession, ChatMessage } from '../types';

interface ChatStore {
  // Current mode/task
  currentMode: TaskType;
  setMode: (mode: TaskType) => void;
  
  // Sessions
  sessions: ChatSession[];
  setSessions: (sessions: ChatSession[]) => void;
  
  // Current session
  currentSession: ChatSession | null;
  setCurrentSession: (session: ChatSession | null) => void;
  
  // Messages in current session
  messages: ChatMessage[];
  setMessages: (messages: ChatMessage[]) => void;
  addMessage: (message: ChatMessage) => void;
  
  // Streaming state
  isStreaming: boolean;
  setIsStreaming: (streaming: boolean) => void;
  
  streamingContent: string;
  setStreamingContent: (content: string) => void;
  appendStreamingContent: (token: string) => void;
  resetStreamingContent: () => void;
  
  // Chapter filter
  selectedChapters: string[];
  setSelectedChapters: (chapters: string[]) => void;
  
  // Reset all state
  reset: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  // Initial state
  currentMode: 'text_summary',
  sessions: [],
  currentSession: null,
  messages: [],
  isStreaming: false,
  streamingContent: '',
  selectedChapters: [],
  
  // Actions
  setMode: (mode) => set({ currentMode: mode }),
  
  setSessions: (sessions) => set({ sessions }),
  
  setCurrentSession: (session) => set({ currentSession: session }),
  
  setMessages: (messages) => set({ messages }),
  
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  
  setIsStreaming: (streaming) => set({ isStreaming: streaming }),
  
  setStreamingContent: (content) => set({ streamingContent: content }),
  
  appendStreamingContent: (token) => set((state) => ({
    streamingContent: state.streamingContent + token
  })),
  
  resetStreamingContent: () => set({ streamingContent: '' }),
  
  setSelectedChapters: (chapters) => set({ selectedChapters: chapters }),
  
  reset: () => set({
    currentMode: 'text_summary',
    sessions: [],
    currentSession: null,
    messages: [],
    isStreaming: false,
    streamingContent: '',
    selectedChapters: []
  })
}));

