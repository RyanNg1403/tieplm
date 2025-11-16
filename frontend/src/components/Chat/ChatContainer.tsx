import React, { useCallback, useEffect, useState, useRef } from 'react';
import { HStack, VStack, Box, useToast, useBreakpointValue, Button, Text, useColorModeValue } from '@chakra-ui/react';
import { ArrowBackIcon } from '@chakra-ui/icons';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { MessageList } from './MessageList';
import { VideoSummaryDisplay } from './VideoSummaryDisplay';
import { ChatInput } from './ChatInput';
import { Sidebar } from './Sidebar';
import { VideoPlayer } from '../VideoPlayer';
import { QuizDisplay } from './QuizDisplay';
import { ResizablePanels } from '../shared/ResizablePanels';
import { useChatStore } from '../../stores/chatStore';
import { useQuizStore } from '../../stores/quizStore';
import { useSSE } from '../../hooks/useSSE';
import { textSummaryAPI, qaAPI, videoSummaryAPI, sessionsAPI, quizAPI } from '../../services/api';
import type { VideoInfo } from '../../services/api';
import { ChatMessage, ChatSession, Quiz, TaskType } from '../../types';
import { getTaskColor } from '../../utils/taskColors';
import { ColorModeSwitcher } from '../ColorModeSwitcher';

interface ChatContainerProps {}

export const ChatContainer: React.FC<ChatContainerProps> = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();

  // Chat store state
  const {
    currentMode,
    setMode,
    messages,
    addMessage,
    setMessages,
    currentSession,
    setCurrentSession,
    isStreaming,
    setIsStreaming,
    streamingContent,
    appendStreamingContent,
    resetStreamingContent,
    selectedChapters: chatSelectedChapters,
    setSelectedChapters: setChatSelectedChapters,
    selectedVideo,
    setSelectedVideo,
  } = useChatStore();

  // Quiz store state
  const {
    currentQuiz,
    setCurrentQuiz,
    persistedQuizId,
    setPersistedQuizId,
    isGenerating,
    setIsGenerating,
    generationProgress,
    setGenerationProgress,
    isValidating,
    setIsValidating,
    addValidationResult,
    clearValidationResults,
    resetQuiz,
    selectedChapters: quizSelectedChapters,
    setSelectedChapters: setQuizSelectedChapters,
    setAnswer,
    clearAnswers,
  } = useQuizStore();

  // Use appropriate state based on mode
  const selectedChapters = currentMode === 'quiz' ? quizSelectedChapters : chatSelectedChapters;
  const setSelectedChapters = currentMode === 'quiz' ? setQuizSelectedChapters : setChatSelectedChapters;

  // Get task-specific color scheme
  const taskColor = getTaskColor(currentMode);

  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [videoLoading, setVideoLoading] = useState<boolean>(false);
  const [videoError, setVideoError] = useState<string | null>(null);
  const videoPlayerRef = useRef<any>(null);
  const [embedStartTime, setEmbedStartTime] = useState<number | null>(null);
  const [isInitialLoad, setIsInitialLoad] = useState<boolean>(true);

  // Responsive layout: side-by-side on desktop (>= 1024px), stacked on mobile
  const isDesktop = useBreakpointValue({ base: false, lg: true }, { ssr: false });

  // Quiz configuration (local state for UI controls)
  const [quizQuestionType, setQuizQuestionType] = useState<string>('mcq');
  const [quizNumQuestions, setQuizNumQuestions] = useState<number>(5);

  // Track previous mode to detect changes
  const prevModeRef = useRef<TaskType>(currentMode);

  // Clear messages when switching between different chat tasks (text_summary, qa, video_summary)
  useEffect(() => {
    const prevMode = prevModeRef.current;

    // Skip on initial mount
    if (prevMode === currentMode) {
      return;
    }

    // Define chat-based tasks (tasks that share the message display)
    const chatTasks: TaskType[] = ['text_summary', 'qa', 'video_summary'];

    // If switching between different chat tasks, clear messages
    const switchingBetweenChatTasks =
      chatTasks.includes(prevMode) &&
      chatTasks.includes(currentMode) &&
      prevMode !== currentMode;

    if (switchingBetweenChatTasks) {
      setMessages([]);
      resetStreamingContent();
      setCurrentSession(null);
    }

    // If switching to quiz mode, clear quiz state
    if (currentMode === 'quiz' && prevMode !== 'quiz') {
      resetQuiz();
    }

    // Update ref for next comparison
    prevModeRef.current = currentMode;
  }, [currentMode, setMessages, resetStreamingContent, setCurrentSession, resetQuiz]);

  // Restore session/quiz on mount (from persisted state)
  useEffect(() => {
    if (!isInitialLoad) return;

    const restoreSession = async () => {
      try {
        if (currentMode === 'quiz' && persistedQuizId) {
          // Restore quiz state
          try {
            const quizData = await quizAPI.getQuiz(persistedQuizId);

            // Restore quiz
            const quiz: Quiz = {
              id: persistedQuizId,
              user_id: 'default_user',
              topic: undefined,
              chapters: undefined,
              question_type: 'mixed',
              num_questions: quizData.questions.length,
              created_at: new Date().toISOString(),
              questions: quizData.questions,
            };

            setCurrentQuiz(quiz);

            // Fetch and restore previous attempts
            const attempts = await quizAPI.getQuizAttempts(persistedQuizId);

            if (attempts.length > 0) {
              // Create maps for lookup
              const questionIdToIndex = new Map<number, number>();
              const questionIdToType = new Map<number, string>();
              const questionIdToCorrectAnswer = new Map<number, string>();
              const questionIdToExplanation = new Map<number, string>();

              quizData.questions.forEach((q: any) => {
                questionIdToIndex.set(q.id, q.question_index);
                questionIdToType.set(q.id, q.question_type);
                questionIdToCorrectAnswer.set(q.id, q.correct_answer);
                questionIdToExplanation.set(q.id, q.explanation);
              });

              // Restore answers and validation results
              attempts.forEach((attempt) => {
                const questionIndex = questionIdToIndex.get(attempt.question_id);
                const questionType = questionIdToType.get(attempt.question_id);
                const correctAnswer = questionIdToCorrectAnswer.get(attempt.question_id);
                const explanation = questionIdToExplanation.get(attempt.question_id);

                if (questionIndex !== undefined && questionType) {
                  // Restore answer
                  setAnswer(questionIndex, attempt.user_answer);

                  // Restore validation result with all required fields
                  const validationResult: any = {
                    question_index: questionIndex,
                    question_type: questionType,
                    user_answer: attempt.user_answer,
                    is_correct: attempt.is_correct,
                    correct_answer: correctAnswer,
                    llm_score: attempt.llm_score,
                    llm_feedback: attempt.llm_feedback,
                    explanation: explanation,
                  };
                  addValidationResult(validationResult);
                }
              });
            }
          } catch (err) {
            // Quiz not found or deleted - clear it
            console.log('Quiz not found, clearing persisted state');
            setPersistedQuizId(null);
          }
        } else if (currentMode === 'video_summary' && selectedVideo) {
          // Video summary mode - video will auto-load via existing effect
        } else if (currentSession?.id && (currentMode === 'text_summary' || currentMode === 'qa')) {
          // Restore chat session messages
          try {
            const sessionMessages = await sessionsAPI.getSessionMessages(currentSession.id);
            setMessages(sessionMessages);
          } catch (err) {
            // Session not found or deleted - clear it
            console.log('Session not found, clearing persisted state');
            setCurrentSession(null);
            setMessages([]);
          }
        }
      } catch (error: any) {
        console.error('Failed to restore session:', error);
      } finally {
        setIsInitialLoad(false);
      }
    };

    restoreSession();
  }, []); // Only run on mount

  // Fetch video metadata when a video is selected
  useEffect(() => {
    let cancelled = false;
    const fetchVideo = async () => {
      if (!selectedVideo) {
        setVideoInfo(null);
        setVideoError(null);
        return;
      }

      setVideoLoading(true);
      setVideoError(null);
      try {
        const info = await videoSummaryAPI.getVideoInfo(selectedVideo);
        if (!cancelled) setVideoInfo(info);
      } catch (err: any) {
        if (!cancelled) setVideoError(err?.message || String(err));
      } finally {
        if (!cancelled) setVideoLoading(false);
      }
    };

    fetchVideo();
    return () => { cancelled = true; };
  }, [selectedVideo]);

  // Auto-load and stream pre-computed summary when video is selected (video_summary mode only)
  useEffect(() => {
    let cancelled = false;

    const loadAndStreamSummary = async () => {
      if (currentMode !== 'video_summary' || !selectedVideo || isStreaming || isInitialLoad) {
        return;
      }

      // Clear previous messages
      setMessages([]);

      try {
        // Fetch pre-computed summary
        const summaryData = await videoSummaryAPI.getVideoSummary(selectedVideo);

        if (cancelled) return;

        if (summaryData.has_summary) {
          // Stream the pre-computed summary word-by-word using POST endpoint
          setIsStreaming(true);
          resetStreamingContent();

          const url = videoSummaryAPI.getSummarizeStreamURL();
          const body = {
            video_id: selectedVideo,
            regenerate: false, // Use pre-computed summary
          };

          await startStream(url, body);
        }
      } catch (err: any) {
        if (!cancelled) {
          console.error('Failed to load summary:', err);
        }
      }
    };

    loadAndStreamSummary();
    return () => { cancelled = true; };
  }, [selectedVideo, currentMode, isInitialLoad]); // Only trigger when video or mode changes

  // Helper to convert YouTube watch/share URLs to embed URLs
  const toYouTubeEmbed = (url: string): string | null => {
    try {
      const u = new URL(url);
      // youtu.be short link
      if (u.hostname.includes('youtu.be')) {
        const id = u.pathname.replace('/', '');
        return `https://www.youtube.com/embed/${id}`;
      }

      // youtube watch URL
      if (u.hostname.includes('youtube.com')) {
        const params = new URLSearchParams(u.search);
        const id = params.get('v');
        if (id) return `https://www.youtube.com/embed/${id}`;
        // fallback: if path contains /embed/
        if (u.pathname.includes('/embed/')) return url;
      }

      return null;
    } catch (e) {
      return null;
    }
  };

  // Reset embed start time when selected video changes
  useEffect(() => {
    setEmbedStartTime(null);
  }, [selectedVideo]);

  // Handle seek requests from messages (timestamps)
  const handleSeek = useCallback((timestamp: number) => {
    const embed = videoInfo ? toYouTubeEmbed(videoInfo.url) : null;
    if (embed) {
      setEmbedStartTime(Math.floor(timestamp));
    } else {
      videoPlayerRef.current?.seekToTime(Math.floor(timestamp));
    }
  }, [videoInfo, videoPlayerRef]);

  // SSE hook
  const { startStream } = useSSE({
    onToken: (token) => {
      appendStreamingContent(token);
    },
    onProgress: (progress) => {
      // Update quiz progress for quiz mode
      if (currentMode === 'quiz') {
        setGenerationProgress(progress);
      }
    },
    onValidation: (result) => {
      // Handle incremental validation results for quiz
      if (currentMode === 'quiz') {
        addValidationResult(result);
      }
    },
    onDone: async (content, sources, sessionId, quizId) => {
      // For quiz mode, parse and store the result
      if (currentMode === 'quiz') {
        setGenerationProgress(100);

        // If we're validating, mark as done
        if (isValidating) {
          setIsValidating(false);
          setIsGenerating(false);

          toast({
            title: 'Validation complete',
            status: 'success',
            duration: 2000,
            isClosable: true,
          });
        } else if (quizId) {
          // Quiz generation complete - fetch full quiz from backend
          try {
            const quizData = await quizAPI.getQuiz(quizId);

            // Create Quiz object
            const quiz: Quiz = {
              id: quizId,
              user_id: 'default_user',
              topic: undefined,
              chapters: selectedChapters.length > 0 ? selectedChapters : undefined,
              question_type: quizQuestionType as 'mcq' | 'open_ended' | 'mixed',
              num_questions: quizData.questions.length,
              created_at: new Date().toISOString(),
              questions: quizData.questions,
            };

            setCurrentQuiz(quiz);
            setIsGenerating(false);

            // Invalidate query cache to refresh the sidebar with new quiz
            queryClient.invalidateQueries({ queryKey: ['sessions', 'quiz'] });

            toast({
              title: 'Quiz generated successfully',
              status: 'success',
              duration: 2000,
              isClosable: true,
            });
          } catch (error: any) {
            console.error('Failed to fetch quiz:', error);
            setIsGenerating(false);

            toast({
              title: 'Error loading quiz',
              description: error.message,
              status: 'error',
              duration: 5000,
              isClosable: true,
            });
          }
        }
      } else {
        // For other modes, add assistant message with sources
        const assistantMessage: ChatMessage = {
          id: Date.now().toString(),
          role: 'assistant',
          content,
          sources,
          created_at: new Date().toISOString(),
        };
        addMessage(assistantMessage);

        // Update current session if we got a new session_id from backend
        if (sessionId && (!currentSession || currentSession.id !== sessionId)) {
          setCurrentSession({ id: sessionId } as ChatSession);
        }

        // Reset streaming state
        resetStreamingContent();
        setIsStreaming(false);

        toast({
          title: 'Response complete',
          status: 'success',
          duration: 2000,
          isClosable: true,
        });
      }
    },
    onError: (error) => {
      setIsStreaming(false);
      setIsGenerating(false);
      setIsValidating(false);
      resetStreamingContent();
      setGenerationProgress(0);

      toast({
        title: 'Error',
        description: error,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
  });

  // Session management
  const handleNewChat = useCallback(() => {
    if (currentMode === 'quiz') {
      // Reset quiz state
      resetQuiz();
    } else {
      // Reset chat state
      setCurrentSession(null);
      setMessages([]);
      resetStreamingContent();
      setChatSelectedChapters([]);
      setSelectedVideo(null);
    }
  }, [currentMode, resetQuiz, setCurrentSession, setMessages, resetStreamingContent, setChatSelectedChapters, setSelectedVideo]);

  const handleSelectSession = useCallback(async (sessionId: string) => {
    try {
      if (currentMode === 'quiz') {
        // Clear previous quiz state first
        clearAnswers();
        clearValidationResults();

        // For quiz mode, fetch the quiz from backend
        const quizData = await quizAPI.getQuiz(sessionId);

        // Create Quiz object
        const quiz: Quiz = {
          id: sessionId,
          user_id: 'default_user',
          topic: undefined,
          chapters: undefined,
          question_type: 'mixed',
          num_questions: quizData.questions.length,
          created_at: new Date().toISOString(),
          questions: quizData.questions,
        };

        setCurrentQuiz(quiz);

        // Fetch and restore previous attempts if any
        try {
          const attempts = await quizAPI.getQuizAttempts(sessionId);

          if (attempts.length > 0) {
            // Create maps for lookup
            const questionIdToIndex = new Map<number, number>();
            const questionIdToType = new Map<number, string>();
            const questionIdToCorrectAnswer = new Map<number, string>();
            const questionIdToExplanation = new Map<number, string>();

            quizData.questions.forEach((q: any) => {
              questionIdToIndex.set(q.id, q.question_index);
              questionIdToType.set(q.id, q.question_type);
              questionIdToCorrectAnswer.set(q.id, q.correct_answer);
              questionIdToExplanation.set(q.id, q.explanation);
            });

            // Restore answers and validation results
            attempts.forEach((attempt) => {
              const questionIndex = questionIdToIndex.get(attempt.question_id);
              const questionType = questionIdToType.get(attempt.question_id);
              const correctAnswer = questionIdToCorrectAnswer.get(attempt.question_id);
              const explanation = questionIdToExplanation.get(attempt.question_id);

              if (questionIndex !== undefined && questionType) {
                // Restore answer
                setAnswer(questionIndex, attempt.user_answer);

                // Restore validation result with all required fields
                const validationResult: any = {
                  question_index: questionIndex,
                  question_type: questionType,
                  user_answer: attempt.user_answer,
                  is_correct: attempt.is_correct,
                  correct_answer: correctAnswer,
                  llm_score: attempt.llm_score,
                  llm_feedback: attempt.llm_feedback,
                  explanation: explanation,
                };
                addValidationResult(validationResult);
              }
            });
          }
        } catch (err) {
          // No attempts yet - that's fine
          console.log('No attempts found for quiz');
        }

        resetStreamingContent();
      } else {
        // For chat modes, fetch messages
        const sessionMessages = await sessionsAPI.getSessionMessages(sessionId);
        setMessages(sessionMessages);
        setCurrentSession({ id: sessionId } as ChatSession);
        resetStreamingContent();
      }
    } catch (error: any) {
      toast({
        title: 'Failed to load session',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  }, [currentMode, setMessages, setCurrentSession, setCurrentQuiz, resetStreamingContent, clearAnswers, clearValidationResults, setAnswer, addValidationResult, toast]);

  const handleDeleteSession = useCallback(async (sessionId: string) => {
    try {
      // Delete quiz or chat session based on current mode
      if (currentMode === 'quiz') {
        await quizAPI.deleteQuiz(sessionId);
        if (currentQuiz?.id === sessionId) {
          handleNewChat();
        }
        // Invalidate query cache to refresh the sidebar
        queryClient.invalidateQueries({ queryKey: ['sessions', 'quiz'] });
        toast({
          title: 'Quiz deleted',
          status: 'success',
          duration: 2000,
          isClosable: true,
        });
      } else {
        await sessionsAPI.deleteSession(sessionId);
        if (currentSession?.id === sessionId) {
          handleNewChat();
        }
        // Invalidate query cache to refresh the sidebar
        queryClient.invalidateQueries({ queryKey: ['sessions', currentMode] });
        toast({
          title: 'Session deleted',
          status: 'success',
          duration: 2000,
          isClosable: true,
        });
      }
    } catch (error: any) {
      toast({
        title: currentMode === 'quiz' ? 'Failed to delete quiz' : 'Failed to delete session',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  }, [currentMode, currentSession, currentQuiz, handleNewChat, queryClient, toast]);

  // Handle send message
  const handleSend = useCallback(async (messageText: string) => {
    // Special markers
    const isVideoSummaryRegenerate = messageText === '__VIDEO_SUMMARY_REGENERATE__';
    const isQuizMode = currentMode === 'quiz';
    const isQuizGenerate = messageText === '__QUIZ_GENERATE__' || isQuizMode;

    // Add user message for chat modes (not for video_summary regenerate or quiz)
    if (!isVideoSummaryRegenerate && !isQuizGenerate) {
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'user',
        content: messageText,
        created_at: new Date().toISOString(),
      };
      addMessage(userMessage);
    }

    // Start streaming
    if (currentMode === 'quiz') {
      resetQuiz(); // Clear previous quiz first
      setIsGenerating(true); // Then set generating state
      setGenerationProgress(0);
    } else {
      setIsStreaming(true);
      resetStreamingContent();
    }

    try {
      // Determine URL and body based on task mode
      let url = '';
      let body: any = {};

      if (currentMode === 'text_summary') {
        url = currentSession
          ? textSummaryAPI.getFollowupStreamURL(currentSession.id)
          : textSummaryAPI.getSummarizeStreamURL();
        body = {
          query: messageText,
          chapters: selectedChapters.length > 0 ? selectedChapters : undefined,
          session_id: currentSession?.id,
        };
      } else if (currentMode === 'qa') {
        url = currentSession
          ? qaAPI.getFollowupStreamURL(currentSession.id)
          : qaAPI.getAskStreamURL();
        body = {
          query: messageText,
          chapters: selectedChapters.length > 0 ? selectedChapters : undefined,
          session_id: currentSession?.id,
        };
      } else if (currentMode === 'video_summary') {
        if (!selectedVideo) {
          throw new Error('Please select a video first');
        }
        url = videoSummaryAPI.getSummarizeStreamURL();
        body = {
          video_id: selectedVideo,
          regenerate: true, // User explicitly clicked "Regenerate" button
        };
      } else if (currentMode === 'quiz') {
        url = quizAPI.getGenerateStreamURL();
        body = {
          query: messageText !== '__QUIZ_GENERATE__' ? messageText : undefined,
          chapters: selectedChapters.length > 0 ? selectedChapters : undefined,
          question_type: quizQuestionType,
          num_questions: quizNumQuestions,
          // No session_id for quiz - uses dedicated quiz tables
        };
      } else {
        throw new Error(`Task ${currentMode} not implemented yet`);
      }

      // Start SSE stream
      await startStream(url, body);

    } catch (error: any) {
      setIsStreaming(false);
      setIsGenerating(false);
      resetStreamingContent();

      toast({
        title: 'Failed to start stream',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  }, [
    currentMode,
    currentSession,
    selectedChapters,
    selectedVideo,
    quizQuestionType,
    quizNumQuestions,
    addMessage,
    setIsStreaming,
    setIsGenerating,
    setGenerationProgress,
    resetStreamingContent,
    resetQuiz,
    startStream,
    toast,
  ]);

  // Handle submit quiz answers
  const handleSubmitAnswers = useCallback(async () => {
    if (!currentQuiz) return;

    const { userAnswers } = useQuizStore.getState();

    // Convert Map to array of answers
    const answers = Array.from(userAnswers.entries()).map(([question_index, answer]) => ({
      question_index,
      answer,
    }));

    setIsValidating(true);
    clearValidationResults();

    try {
      const url = quizAPI.getValidateStreamURL();
      const body = {
        quiz_id: currentQuiz.id,
        answers,
      };

      // Start SSE stream for validation
      await startStream(url, body);

    } catch (error: any) {
      setIsValidating(false);

      toast({
        title: 'Failed to validate answers',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  }, [currentQuiz, setIsValidating, clearValidationResults, startStream, toast]);

  return (
    <HStack h="100vh" spacing={0} align="stretch">
      {/* Sidebar - Hide for video_summary mode since it doesn't use chat sessions */}
      {currentMode !== 'video_summary' && (
        <Sidebar
          currentSessionId={currentMode === 'quiz' ? currentQuiz?.id || null : currentSession?.id || null}
          taskType={currentMode}
          colorScheme={taskColor}
          onNewChat={handleNewChat}
          onSelectSession={handleSelectSession}
          onDeleteSession={handleDeleteSession}
        />
      )}
      
      {/* Video Summary Layout with Resizable Panels */}
      {currentMode === 'video_summary' && (
        <VStack flex={1} spacing={0} align="stretch" h="100vh" overflow="hidden">
          {/* Header */}
          <Box
            w="full"
            bg={useColorModeValue('white', 'gray.800')}
            borderBottom="1px"
            borderColor={useColorModeValue('gray.200', 'gray.700')}
            p={4}
            display="flex"
            alignItems="center"
            justifyContent="center"
            flexShrink={0}
            position="relative"
          >
            <Button
              position="absolute"
              left={4}
              colorScheme={taskColor}
              variant="solid"
              onClick={() => navigate('/')}
              size="md"
              leftIcon={<ArrowBackIcon />}
              fontWeight="semibold"
              boxShadow="md"
              _hover={{
                transform: 'translateY(-2px)',
                boxShadow: 'lg',
              }}
              transition="all 0.2s"
            >
              Home
            </Button>
            <ColorModeSwitcher position="absolute" />
            <Text fontWeight="bold" fontSize="lg" textAlign="center">
              Video Summary & Chat
            </Text>
          </Box>

          {/* Main Content Area - Responsive Layout */}
          {isDesktop ? (
            // Desktop: Side-by-side resizable panels
            <Box flex={1} minH={0} overflow="hidden">
              <ResizablePanels
                direction="horizontal"
                defaultSizes={[55, 45]}
                minSizes={[30, 30]}
              >
                {/* Left Panel: Video Player */}
                <Box
                  w="full"
                  h="full"
                  display="flex"
                  flexDirection="column"
                  bg="gray.900"
                  overflow="hidden"
                >
                  {selectedVideo ? (
                    videoLoading ? (
                      <Box
                        bg="gray.700"
                        w="full"
                        h="full"
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                        color="gray.400"
                        fontSize="sm"
                      >
                        Loading video...
                      </Box>
                    ) : videoError ? (
                      <Box
                        bg="red.600"
                        w="full"
                        h="full"
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                        color="white"
                        fontSize="sm"
                      >
                        Error loading video
                      </Box>
                    ) : videoInfo ? (
                      (() => {
                        const embed = toYouTubeEmbed(videoInfo.url);
                        if (embed) {
                          const srcWithStart = embed + (embedStartTime !== null ? `${embed.includes('?') ? '&' : '?'}start=${embedStartTime}&autoplay=1` : '');
                          return (
                            <Box w="full" h="full" overflow="hidden">
                              <Box as="iframe" src={srcWithStart} width="100%" height="100%" border={0} />
                            </Box>
                          );
                        }
                        return <VideoPlayer ref={videoPlayerRef} videoUrl={videoInfo.url} videoTitle={videoInfo.title} />;
                      })()
                    ) : (
                      <Box
                        bg="gray.700"
                        w="full"
                        h="full"
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                        color="gray.400"
                        fontSize="sm"
                      >
                        Video Player
                      </Box>
                    )
                  ) : (
                    <Box
                      bg="gray.800"
                      w="full"
                      h="full"
                      display="flex"
                      alignItems="center"
                      justifyContent="center"
                      color="gray.300"
                      fontSize="sm"
                    >
                      Please select a video from the dropdown
                    </Box>
                  )}
                </Box>

                {/* Right Panel: Summary */}
                <VStack
                  flex={1}
                  spacing={0}
                  bg={useColorModeValue('gray.50', 'gray.900')}
                  align="stretch"
                  h="full"
                  overflow="hidden"
                >
                  {/* Summary Display Area - Full width for video_summary */}
                  <Box flex={1} minH={0} h="full" overflow="hidden" position="relative">
                    <VideoSummaryDisplay
                      messages={messages}
                      isStreaming={isStreaming}
                      streamingContent={streamingContent}
                      onSeekVideo={handleSeek}
                    />
                  </Box>

                  {/* Input Area */}
                  <Box flexShrink={0}>
                    <ChatInput
                      currentMode={currentMode}
                      colorScheme={taskColor}
                      onModeChange={setMode}
                      onSend={handleSend}
                      isStreaming={isStreaming}
                      selectedChapters={selectedChapters}
                      onChaptersChange={setSelectedChapters}
                      selectedVideo={selectedVideo}
                      onVideoChange={setSelectedVideo}
                    />
                  </Box>
                </VStack>
              </ResizablePanels>
            </Box>
          ) : (
            // Mobile: Stacked layout with resizable vertical panels
            <Box flex={1} minH={0} overflow="hidden">
              <ResizablePanels
                direction="vertical"
                defaultSizes={[60, 40]}
                minSizes={[30, 30]}
              >
                {/* Top Panel: Video Player */}
                <Box
                  w="full"
                  h="full"
                  display="flex"
                  flexDirection="column"
                  bg="gray.900"
                  overflow="hidden"
                >
                  {selectedVideo ? (
                    videoLoading ? (
                      <Box
                        bg="gray.700"
                        w="full"
                        h="full"
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                        color="gray.400"
                        fontSize="sm"
                      >
                        Loading video...
                      </Box>
                    ) : videoError ? (
                      <Box
                        bg="red.600"
                        w="full"
                        h="full"
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                        color="white"
                        fontSize="sm"
                      >
                        Error loading video
                      </Box>
                    ) : videoInfo ? (
                      (() => {
                        const embed = toYouTubeEmbed(videoInfo.url);
                        if (embed) {
                          const srcWithStart = embed + (embedStartTime !== null ? `${embed.includes('?') ? '&' : '?'}start=${embedStartTime}&autoplay=1` : '');
                          return (
                            <Box w="full" h="full" overflow="hidden">
                              <Box as="iframe" src={srcWithStart} width="100%" height="100%" border={0} />
                            </Box>
                          );
                        }
                        return <VideoPlayer ref={videoPlayerRef} videoUrl={videoInfo.url} videoTitle={videoInfo.title} />;
                      })()
                    ) : (
                      <Box
                        bg="gray.700"
                        w="full"
                        h="full"
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                        color="gray.400"
                        fontSize="sm"
                      >
                        Video Player
                      </Box>
                    )
                  ) : (
                    <Box
                      bg="gray.800"
                      w="full"
                      h="full"
                      display="flex"
                      alignItems="center"
                      justifyContent="center"
                      color="gray.300"
                      fontSize="sm"
                    >
                      Please select a video from the dropdown
                    </Box>
                  )}
                </Box>

                {/* Bottom Panel: Summary */}
                <VStack
                  flex={1}
                  spacing={0}
                  bg={useColorModeValue('gray.50', 'gray.900')}
                  align="stretch"
                  h="full"
                  overflow="hidden"
                >
                  {/* Summary Display Area - Full width for video_summary */}
                  <Box flex={1} minH={0} h="full" overflow="hidden" position="relative">
                    <VideoSummaryDisplay
                      messages={messages}
                      isStreaming={isStreaming}
                      streamingContent={streamingContent}
                      onSeekVideo={handleSeek}
                    />
                  </Box>

                  {/* Input Area */}
                  <Box flexShrink={0}>
                    <ChatInput
                      currentMode={currentMode}
                      colorScheme={taskColor}
                      onModeChange={setMode}
                      onSend={handleSend}
                      isStreaming={isStreaming}
                      selectedChapters={selectedChapters}
                      onChaptersChange={setSelectedChapters}
                      selectedVideo={selectedVideo}
                      onVideoChange={setSelectedVideo}
                    />
                  </Box>
                </VStack>
              </ResizablePanels>
            </Box>
          )}
        </VStack>
      )}

      {/* Standard Layout (for text_summary, qa, etc.) */}
      {currentMode !== 'video_summary' && (
        <VStack flex={1} spacing={0} bg={useColorModeValue('gray.50', 'gray.900')}>
          {/* Header */}
          <Box
            w="full"
            bg={useColorModeValue('white', 'gray.800')}
            borderBottom="1px"
            borderColor={useColorModeValue('gray.200', 'gray.700')}
            p={4}
            display="flex"
            alignItems="center"
            justifyContent="center"
            position="relative"
          >
            <Button
              position="absolute"
              left={4}
              colorScheme={taskColor}
              variant="solid"
              onClick={() => navigate('/')}
              size="md"
              leftIcon={<ArrowBackIcon />}
              fontWeight="semibold"
              boxShadow="md"
              _hover={{
                transform: 'translateY(-2px)',
                boxShadow: 'lg',
              }}
              transition="all 0.2s"
            >
              Home
            </Button>
            <ColorModeSwitcher position="absolute" />
            <Text fontWeight="bold" fontSize="lg" textAlign="center">
              TiepLM: One-for-all AI Assistant - CS431 Deep Learning
            </Text>
          </Box>

          {/* Messages Area / Quiz Display */}
          {currentMode !== 'quiz' ? (
            <MessageList
              messages={messages}
              isStreaming={isStreaming}
              streamingContent={streamingContent}
            />
          ) : (
            <QuizDisplay
              quiz={currentQuiz}
              colorScheme={taskColor}
              isGenerating={isGenerating}
              generationProgress={generationProgress}
              isValidating={isValidating}
              onSubmitAnswers={handleSubmitAnswers}
            />
          )}

          {/* Input Area */}
          <ChatInput
            currentMode={currentMode}
            colorScheme={taskColor}
            onModeChange={setMode}
            onSend={handleSend}
            isStreaming={isStreaming}
            selectedChapters={selectedChapters}
            onChaptersChange={setSelectedChapters}
            selectedVideo={selectedVideo}
            onVideoChange={setSelectedVideo}
            quizQuestionType={quizQuestionType}
            onQuizQuestionTypeChange={setQuizQuestionType}
            quizNumQuestions={quizNumQuestions}
            onQuizNumQuestionsChange={setQuizNumQuestions}
          />
        </VStack>
      )}
    </HStack>
  );
};

