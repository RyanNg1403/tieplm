/**
 * Message component with citation support
 */
import React, { useState } from 'react';
import { Box, Link, VStack, HStack, Button } from '@chakra-ui/react';
import ReactMarkdown from 'react-markdown';
import { ChatMessage, SourceReference } from '../../types';
import { SourcesModal } from './SourcesModal';

interface MessageProps {
  message: ChatMessage;
}

export const Message: React.FC<MessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const [isSourcesModalOpen, setIsSourcesModalOpen] = useState(false);
  
  // Handle citation clicks
  const handleCitationClick = (index: number, sources?: SourceReference[]) => {
    if (!sources || index > sources.length) return;
    
    const source = sources[index - 1]; // Citations are 1-indexed
    if (!source) return;
    
    // Construct YouTube URL with timestamp
    const url = `${source.video_url}&t=${source.start_time}s`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };
  
  // Replace citations [1], [2], etc. with clickable links
  const renderContentWithCitations = (content: string, sources?: SourceReference[]) => {
    if (!sources || sources.length === 0) {
      return <ReactMarkdown>{content}</ReactMarkdown>;
    }
    
    // Split content by citation pattern [N]
    const citationRegex = /\[(\d+)\]/g;
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match;
    
    while ((match = citationRegex.exec(content)) !== null) {
      // Add text before citation
      if (match.index > lastIndex) {
        const textBefore = content.slice(lastIndex, match.index);
        parts.push(
          <ReactMarkdown key={`text-${lastIndex}`}>{textBefore}</ReactMarkdown>
        );
      }
      
      // Add clickable citation
      const citationIndex = parseInt(match[1]);
      parts.push(
        <Link
          key={`citation-${match.index}`}
          color="blue.500"
          fontWeight="bold"
          cursor="pointer"
          onClick={() => handleCitationClick(citationIndex, sources)}
          _hover={{ textDecoration: 'underline' }}
        >
          [{citationIndex}]
        </Link>
      );
      
      lastIndex = match.index + match[0].length;
    }
    
    // Add remaining text
    if (lastIndex < content.length) {
      const textAfter = content.slice(lastIndex);
      parts.push(
        <ReactMarkdown key={`text-${lastIndex}`}>{textAfter}</ReactMarkdown>
      );
    }
    
    return <Box>{parts}</Box>;
  };
  
  return (
    <>
      <HStack
        align="flex-start"
        justify={isUser ? 'flex-end' : 'flex-start'}
        w="full"
        mb={4}
      >
        <Box
          maxW="75%"
          bg={isUser ? 'blue.500' : 'gray.100'}
          color={isUser ? 'white' : 'black'}
          px={4}
          py={3}
          borderRadius="lg"
          boxShadow="sm"
        >
          <VStack align="stretch" spacing={2}>
            {/* Message content */}
            <Box>
              {renderContentWithCitations(message.content, message.sources)}
            </Box>
            
            {/* Show sources button if available (only for assistant messages) */}
            {!isUser && message.sources && message.sources.length > 0 && (
              <HStack spacing={2} flexWrap="wrap" mt={1}>
                <Button
                  size="sm"
                  colorScheme="green"
                  variant="solid"
                  onClick={() => setIsSourcesModalOpen(true)}
                  fontSize="xs"
                  height="26px"
                  px={3}
                  _hover={{
                    bg: 'green.600',
                    transform: 'translateY(-1px)',
                  }}
                  transition="all 0.2s"
                >
                  {message.sources.length} nguồn
                </Button>
              </HStack>
            )}
          </VStack>
        </Box>
      </HStack>
      
      {/* Sources Modal */}
      {message.sources && message.sources.length > 0 && (
        <SourcesModal
          isOpen={isSourcesModalOpen}
          onClose={() => setIsSourcesModalOpen(false)}
          sources={message.sources}
        />
      )}
    </>
  );
};

