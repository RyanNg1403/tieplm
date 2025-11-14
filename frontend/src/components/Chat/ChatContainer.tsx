/**
 * ChatContainer - main chat interface
 */
import React, { useCallback } from 'react';
import { HStack, VStack, Box, useToast } from '@chakra-ui/react';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { Sidebar } from './Sidebar';
import { useChatStore } from '../../stores/chatStore';
import { useSSE } from '../../hooks/useSSE';
import { textSummaryAPI, qaAPI, sessionsAPI } from '../../services/api';
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
  } = useChatStore();
  
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
  }, [setCurrentSession, setMessages, resetStreamingContent, setSelectedChapters]);

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
      // Determine URL based on task mode and session
      let url = '';
      
      if (currentMode === 'text_summary') {
        url = currentSession
          ? textSummaryAPI.getFollowupStreamURL(currentSession.id)
          : textSummaryAPI.getSummarizeStreamURL();
      } else if (currentMode === 'qa') {
        url = currentSession
          ? qaAPI.getFollowupStreamURL(currentSession.id)
          : qaAPI.getAskStreamURL();
      } else {
        throw new Error(`Task ${currentMode} not implemented yet`);
      }
      
      // Prepare request body
      const body = {
        query: messageText,
        chapters: selectedChapters.length > 0 ? selectedChapters : undefined,
        session_id: currentSession?.id,
      };
      
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
      
      {/* Main Chat Area */}
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
        />
      </VStack>
    </HStack>
  );
};

