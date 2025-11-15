import React, { useCallback, useEffect, useState, useRef } from 'react';
import { HStack, VStack, Box, useToast } from '@chakra-ui/react';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { Sidebar } from './Sidebar';
import { VideoPlayer } from '../VideoPlayer';
import { QuizDisplay } from '../Quiz/QuizDisplay';
import { useChatStore } from '../../stores/chatStore';
import { useSSE } from '../../hooks/useSSE';
import { textSummaryAPI, qaAPI, videoSummaryAPI, sessionsAPI, quizAPI, QuizQuestion } from '../../services/api';
import type { VideoInfo } from '../../services/api';
import { ChatMessage, ChatSession } from '../../types';

export const ChatContainer: React.FC = () => {
  const toast = useToast();

  // Store state
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
    selectedChapters,
    setSelectedChapters,
    selectedVideo,
    setSelectedVideo,
  } = useChatStore();

  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [videoLoading, setVideoLoading] = useState<boolean>(false);
  const [videoError, setVideoError] = useState<string | null>(null);
  const videoPlayerRef = useRef<any>(null);
  const [embedStartTime, setEmbedStartTime] = useState<number | null>(null);

  // Quiz state
  const [quizProgress, setQuizProgress] = useState<number>(0);
  const [quizQuestions, setQuizQuestions] = useState<QuizQuestion[]>([]);
  const [quizQuestionType, setQuizQuestionType] = useState<string>('mcq');
  const [quizNumQuestions, setQuizNumQuestions] = useState<number>(5);

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
        setQuizProgress(progress);
      }
    },
    onDone: (content, sources, sessionId) => {
      // For quiz mode, parse and store the result
      if (currentMode === 'quiz') {
        setQuizProgress(100);

        // Parse the JSON content to extract questions
        try {
          const questions: QuizQuestion[] = JSON.parse(content);
          if (Array.isArray(questions)) {
            setQuizQuestions(questions);
          } else {
            setQuizQuestions([]);
          }
        } catch (e) {
          console.error('Failed to parse quiz JSON:', e);
          setQuizQuestions([]);
        }

        // Update current session if we got a new session_id from backend
        if (sessionId && (!currentSession || currentSession.id !== sessionId)) {
          setCurrentSession({ id: sessionId } as ChatSession);
        }

        // Reset streaming state
        resetStreamingContent();
        setIsStreaming(false);

        toast({
          title: 'Quiz generated successfully',
          status: 'success',
          duration: 2000,
          isClosable: true,
        });
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
      resetStreamingContent();
      setQuizProgress(0);

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
    setCurrentSession(null);
    setMessages([]);
    resetStreamingContent();
    setSelectedChapters([]);
    setSelectedVideo(null);
    setQuizProgress(0);
    setQuizQuestions([]);
  }, [setCurrentSession, setMessages, resetStreamingContent, setSelectedChapters, setSelectedVideo, setQuizProgress, setQuizQuestions]);

  const handleSelectSession = useCallback(async (sessionId: string) => {
    try {
      const sessionMessages = await sessionsAPI.getSessionMessages(sessionId);
      // Try to parse the content to see if it's a quiz JSON. If fails, fallback to original messages
      try {
        const parsed = JSON.parse(sessionMessages[0].content);
        setQuizQuestions(parsed);
        setMessages([]);
        setMode('quiz');
      } catch (e) {
        setMessages(sessionMessages);
      }
      setCurrentSession({ id: sessionId } as ChatSession); // Simplified, full session from sessions list
      resetStreamingContent();
    } catch (error: any) {
      toast({
        title: 'Failed to load session',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  }, [setMessages, setCurrentSession, resetStreamingContent, toast]);

  const handleDeleteSession = useCallback(async (sessionId: string) => {
    try {
      await sessionsAPI.deleteSession(sessionId);
      if (currentSession?.id === sessionId) {
        handleNewChat();
      }
      toast({
        title: 'Session deleted',
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
    } catch (error: any) {
      toast({
        title: 'Failed to delete session',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  }, [currentSession, handleNewChat, toast]);

  // Handle send message
  const handleSend = useCallback(async (messageText: string) => {
    // Add user message immediately
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: messageText,
      created_at: new Date().toISOString(),
    };
    addMessage(userMessage);

    // Start streaming
    setIsStreaming(true);
    resetStreamingContent();

    // Reset quiz state for quiz mode
    if (currentMode === 'quiz') {
      setQuizProgress(0);
      setQuizQuestions([]);
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
          session_id: currentSession?.id,
        };
      } else if (currentMode === 'quiz') {
        url = quizAPI.getGenerateStreamURL()
        body = {
          query: messageText,
          chapters: selectedChapters.length > 0 ? selectedChapters : undefined,
          video_ids: ["Chương 7_TqKBlC-zyKY", "Chương 8_S8__bXkLSbM"],
          question_type: quizQuestionType,
          num_questions: quizNumQuestions,
          session_id: currentSession?.id,
        };
      } else {
        throw new Error(`Task ${currentMode} not implemented yet`);
      }

      // Start SSE stream
      await startStream(url, body);

    } catch (error: any) {
      setIsStreaming(false);
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
    resetStreamingContent,
    startStream,
    toast,
  ]);

  return (
    <HStack h="100vh" spacing={0} align="stretch">
      {/* Sidebar */}
      <Sidebar
        currentSessionId={currentSession?.id || null}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
      />

      {/* Video Summary Layout (Title -> Video -> Summary) */}
      {currentMode === 'video_summary' && (
        <VStack flex={1} spacing={0} align="stretch">
          {/* Header */}
          <Box
            w="full"
            bg="white"
            borderBottom="1px"
            borderColor="gray.200"
            p={4}
            textAlign="center"
            fontWeight="bold"
            fontSize="lg"
          >
            Video Summary & Chat
          </Box>

          {/* Video Player Area (Middle - Takes maximum available space) */}
          <Box flex={1} w="full" display="flex" flexDirection="column" minH={0} bg="gray.900">
            {/* If a video is selected, show the player; otherwise prompt selection */}
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
                Please select a video from the sidebar
              </Box>
            )}
          </Box>

          {/* Summary Area (Bottom) */}
          <VStack flex={0} spacing={0} bg="gray.50" align="stretch" maxH="50%">
            {/* Messages Area */}
            <MessageList
              messages={messages}
              isStreaming={isStreaming}
              streamingContent={streamingContent}
              onSeekVideo={handleSeek}
            />

            {/* Input Area */}
            <ChatInput
              currentMode={currentMode}
              onModeChange={setMode}
              onSend={handleSend}
              isStreaming={isStreaming}
              selectedChapters={selectedChapters}
              onChaptersChange={setSelectedChapters}
              selectedVideo={selectedVideo}
              onVideoChange={setSelectedVideo}
            />
          </VStack>
        </VStack>
      )}

      {/* Standard Layout (for text_summary, qa, etc.) */}
      {currentMode !== 'video_summary' && (
        <VStack flex={1} spacing={0} bg="gray.50">
          {/* Header */}
          <Box
            w="full"
            bg="white"
            borderBottom="1px"
            borderColor="gray.200"
            p={4}
            textAlign="center"
            fontWeight="bold"
            fontSize="lg"
          >
            Tieplm AI Assistant - CS431 Deep Learning
          </Box>

          {/* Messages Area */}
          {currentMode !== 'quiz' ? (
            <MessageList
              messages={messages}
              isStreaming={isStreaming}
              streamingContent={streamingContent}
            />
          ) : (
            <Box
              flex={1}
              w="full"
              overflow="auto"
              bg="gray.50"
              borderTop="1px"
              borderColor="gray.200"
            >
              <QuizDisplay questions={quizQuestions} />
            </Box>
          )}

          {/* Quiz Progress Bar */}
          {currentMode === 'quiz' && isStreaming && quizProgress > 0 && (
            <Box w="full" px={4} py={2} bg="white" borderTop="1px" borderColor="gray.200">
              <Box fontSize="sm" mb={2} color="gray.600">
                Generating quiz... {quizProgress}%
              </Box>
              <Box w="full" h="8px" bg="gray.200" borderRadius="md" overflow="hidden">
                <Box
                  h="full"
                  bg="blue.500"
                  transition="width 0.3s ease"
                  style={{ width: `${quizProgress}%` }}
                />
              </Box>
            </Box>
          )}

          {/* Quiz Result Display */}
          {/* {currentMode === 'quiz' && quizQuestions.length > 0 && (
            <Box
              flex={1}
              w="full"
              overflow="auto"
              bg="gray.50"
              borderTop="1px"
              borderColor="gray.200"
            >
              <QuizDisplay questions={quizQuestions} />
            </Box>
          )} */}

          {/* Input Area */}
          <ChatInput
            currentMode={currentMode}
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

