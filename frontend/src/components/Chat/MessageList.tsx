/**
 * MessageList component - scrollable list of messages
 */
import React, { useEffect, useRef } from 'react';
import { VStack, Box, Spinner, Text, useColorModeValue } from '@chakra-ui/react';
import { Message } from './Message';
import { ChatMessage } from '../../types';

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingContent: string;
  onSeekVideo?: (timestamp: number) => void;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isStreaming,
  streamingContent,
  onSeekVideo,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Color mode values
  const loadingBg = useColorModeValue('gray.100', 'gray.700');
  const loadingTextColor = useColorModeValue('gray.600', 'gray.300');

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  return (
    <Box
      flex={1}
      w="full"
      h="full"
      overflowY="auto"
      overflowX="hidden"
      p={4}
    >
      <VStack
        spacing={0}
        align="stretch"
        w="full"
      >
        {/* Render all messages */}
        {messages.map((message) => (
          <Message key={message.id} message={message} onSeekVideo={onSeekVideo} />
        ))}

        {/* Show loading indicator when streaming starts (before first token) */}
        {isStreaming && !streamingContent && (
          <Box
            maxW="75%"
            bg={loadingBg}
            px={4}
            py={3}
            borderRadius="lg"
            boxShadow="sm"
            mb={4}
            display="flex"
            alignItems="center"
            gap={2}
          >
            <Spinner size="sm" color="blue.500" />
            <Text fontSize="sm" color={loadingTextColor}>Generating response...</Text>
          </Box>
        )}

        {/* Show streaming message */}
        {isStreaming && streamingContent && (
          <Box
            maxW="75%"
            bg={loadingBg}
            color={useColorModeValue('black', 'white')}
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
    </Box>
  );
};

