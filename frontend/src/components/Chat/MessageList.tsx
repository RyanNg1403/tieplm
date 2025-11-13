/**
 * MessageList component - scrollable list of messages
 */
import React, { useEffect, useRef } from 'react';
import { VStack, Box, Spinner, Text } from '@chakra-ui/react';
import { Message } from './Message';
import { ChatMessage } from '../../types';

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingContent: string;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isStreaming,
  streamingContent
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);
  
  return (
    <VStack
      flex={1}
      w="full"
      spacing={0}
      overflowY="auto"
      p={4}
      align="stretch"
    >
      {/* Render all messages */}
      {messages.map((message) => (
        <Message key={message.id} message={message} />
      ))}
      
      {/* Show streaming message */}
      {isStreaming && streamingContent && (
        <Box
          maxW="75%"
          bg="gray.100"
          px={4}
          py={3}
          borderRadius="lg"
          boxShadow="sm"
          mb={4}
        >
          <Text whiteSpace="pre-wrap">{streamingContent}</Text>
          <Spinner size="sm" mt={2} />
        </Box>
      )}
      
      {/* Scroll anchor */}
      <div ref={messagesEndRef} />
    </VStack>
  );
};

