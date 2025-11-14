import React, { useCallback, useEffect, useState, useRef } from 'react';
import { HStack, VStack, Box, useToast } from '@chakra-ui/react';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { Sidebar } from './Sidebar';
import { VideoPlayer } from '../VideoPlayer';
import { useChatStore } from '../../stores/chatStore';
import { useSSE } from '../../hooks/useSSE';
import { textSummaryAPI, qaAPI, videoSummaryAPI, sessionsAPI } from '../../services/api';
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
  
  // SSE hook
  const { startStream } = useSSE({
    onToken: (token) => {
      appendStreamingContent(token);
    },
    onDone: (content, sources, sessionId) => {
      // Add assistant message with sources
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
    },
    onError: (error) => {
      setIsStreaming(false);
      resetStreamingContent();
      
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
  }, [setCurrentSession, setMessages, resetStreamingContent, setSelectedChapters, setSelectedVideo]);

  const handleSelectSession = useCallback(async (sessionId: string) => {
    try {
      const sessionMessages = await sessionsAPI.getSessionMessages(sessionId);
      setMessages(sessionMessages);
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
      
      {/* Video Summary Layout (side-by-side) */}
      {currentMode === 'video_summary' && (
        <HStack flex={1} spacing={0} align="stretch">
          {/* Video Player (Left) */}
          <VStack flex={0.4} spacing={0} bg="black">
            <Box w="full" p={4}>
              {/* If a video is selected, show the player; otherwise prompt selection */}
              {selectedVideo ? (
                videoLoading ? (
                  <Box
                    bg="gray.700"
                    borderRadius="md"
                    overflow="hidden"
                    w="full"
                    aspectRatio="16/9"
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
                    borderRadius="md"
                    overflow="hidden"
                    w="full"
                    aspectRatio="16/9"
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
                      return (
                        <Box w="full" h="100%" borderRadius="md" overflow="hidden">
                          <Box as="iframe" src={embed} width="100%" height="100%" border={0} />
                        </Box>
                      );
                    }
                    return <VideoPlayer ref={videoPlayerRef} videoUrl={videoInfo.url} videoTitle={videoInfo.title} />;
                  })()
                ) : (
                  <Box
                    bg="gray.700"
                    borderRadius="md"
                    overflow="hidden"
                    w="full"
                    aspectRatio="16/9"
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
                  borderRadius="md"
                  overflow="hidden"
                  w="full"
                  aspectRatio="16/9"
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
          </VStack>

          {/* Summary Area (Right) */}
          <VStack flex={0.6} spacing={0} bg="gray.50">
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
              Video Summary
            </Box>
            
            {/* Messages Area */}
            <MessageList
              messages={messages}
              isStreaming={isStreaming}
              streamingContent={streamingContent}
              onSeekVideo={(timestamp) => videoPlayerRef.current?.seekToTime(timestamp)}
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
        </HStack>
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
          <MessageList
            messages={messages}
            isStreaming={isStreaming}
            streamingContent={streamingContent}
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
      )}
    </HStack>
  );
};

