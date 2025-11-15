/**
 * VideoSummaryDisplay component - displays video summary spanning full width
 */
import React, { useEffect, useRef } from 'react';
import { VStack, Box, Spinner, Text, Link, Button, HStack } from '@chakra-ui/react';
import ReactMarkdown from 'react-markdown';
import { ChatMessage, SourceReference } from '../../types';
import { SourcesModal } from './SourcesModal';

interface VideoSummaryDisplayProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingContent: string;
  onSeekVideo?: (timestamp: number) => void;
}

export const VideoSummaryDisplay: React.FC<VideoSummaryDisplayProps> = ({
  messages,
  isStreaming,
  streamingContent,
  onSeekVideo,
}) => {
  const contentEndRef = useRef<HTMLDivElement>(null);
  const [isSourcesModalOpen, setIsSourcesModalOpen] = React.useState(false);

  // Auto-scroll to bottom when content changes
  useEffect(() => {
    contentEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // Handle citation clicks
  const handleCitationClick = (index: number, sources?: SourceReference[]) => {
    if (!sources || index > sources.length) return;

    const source = sources[index - 1]; // Citations are 1-indexed
    if (!source) return;

    // Seek in embedded player
    if (onSeekVideo) {
      onSeekVideo(source.start_time);
    } else {
      // Otherwise, open YouTube URL with timestamp
      const url = `${source.video_url}&t=${source.start_time}s`;
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  };

  // Helper function to process text and replace citations with clickable links
  const processTextWithCitations = (text: string, sources: SourceReference[]) => {
    const citationRegex = /\[(\d+)\]/g;
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match;

    while ((match = citationRegex.exec(text)) !== null) {
      // Add text before citation
      if (match.index > lastIndex) {
        parts.push(text.slice(lastIndex, match.index));
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
          display="inline"
        >
          [{citationIndex}]
        </Link>
      );

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex));
    }

    return parts.length > 0 ? <>{parts}</> : text;
  };

  // Render content with citations
  const renderContentWithCitations = (content: string, sources?: SourceReference[]) => {
    if (!sources || sources.length === 0) {
      return (
        <Box className="markdown-content">
          <ReactMarkdown>{content}</ReactMarkdown>
        </Box>
      );
    }

    // Custom text renderer to replace citations inline
    const components = {
      p: ({ children, ...props }: any) => {
        const processedChildren = React.Children.map(children, (child) => {
          if (typeof child === 'string') {
            return processTextWithCitations(child, sources);
          }
          return child;
        });
        return <p {...props}>{processedChildren}</p>;
      },
      li: ({ children, ...props }: any) => {
        const processedChildren = React.Children.map(children, (child) => {
          if (typeof child === 'string') {
            return processTextWithCitations(child, sources);
          }
          return child;
        });
        return <li {...props}>{processedChildren}</li>;
      },
    };

    return (
      <Box className="markdown-content">
        <ReactMarkdown components={components}>{content}</ReactMarkdown>
      </Box>
    );
  };

  // Get the latest summary message (last assistant message)
  const summaryMessage = messages.length > 0 ? messages[messages.length - 1] : null;

  return (
    <>
      <Box
        flex={1}
        w="full"
        h="full"
        overflowY="auto"
        overflowX="hidden"
        p={6}
        bg="white"
      >
        <VStack spacing={4} align="stretch" w="full">
          {/* Display completed summary */}
          {summaryMessage && summaryMessage.role === 'assistant' && (
            <>
              {renderContentWithCitations(summaryMessage.content, summaryMessage.sources)}

              {/* Show sources button if available */}
              {summaryMessage.sources && summaryMessage.sources.length > 0 && (
                <HStack spacing={2} mt={4}>
                  <Button
                    size="sm"
                    colorScheme="green"
                    variant="solid"
                    onClick={() => setIsSourcesModalOpen(true)}
                    fontSize="xs"
                    height="28px"
                    px={4}
                  >
                    {summaryMessage.sources.length} nguồn
                  </Button>
                </HStack>
              )}
            </>
          )}

          {/* Show streaming content */}
          {isStreaming && streamingContent && (
            <Box>
              <Text whiteSpace="pre-wrap" className="markdown-content">
                {streamingContent}
              </Text>
              <Spinner size="sm" mt={2} color="blue.500" />
            </Box>
          )}

          {/* Scroll anchor */}
          <div ref={contentEndRef} />
        </VStack>
      </Box>

      {/* Sources Modal */}
      {summaryMessage?.sources && summaryMessage.sources.length > 0 && (
        <SourcesModal
          isOpen={isSourcesModalOpen}
          onClose={() => setIsSourcesModalOpen(false)}
          sources={summaryMessage.sources}
        />
      )}
    </>
  );
};
