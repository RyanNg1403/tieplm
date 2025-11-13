/**
 * SourcesModal - Popup showing all sources with video names and clickable timestamps
 */
import React from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  VStack,
  HStack,
  Text,
  Link,
  Box,
  Badge,
} from '@chakra-ui/react';
import { ExternalLinkIcon } from '@chakra-ui/icons';
import { SourceReference } from '../../types';

interface SourcesModalProps {
  isOpen: boolean;
  onClose: () => void;
  sources: SourceReference[];
}

export const SourcesModal: React.FC<SourcesModalProps> = ({
  isOpen,
  onClose,
  sources,
}) => {
  const handleSourceClick = (source: SourceReference) => {
    const url = `${source.video_url}&t=${source.start_time}s`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          Nguồn tham khảo ({sources.length} video)
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          <VStack align="stretch" spacing={3}>
            {sources.map((source, idx) => (
              <Box
                key={idx}
                p={4}
                borderWidth="1px"
                borderRadius="md"
                borderColor="gray.200"
                _hover={{ bg: 'gray.50', borderColor: 'blue.300' }}
                transition="all 0.2s"
              >
                <HStack spacing={2} mb={2}>
                  <Badge colorScheme="blue" fontSize="sm">
                    [{source.index}]
                  </Badge>
                  <Badge colorScheme="green" fontSize="xs">
                    {source.chapter}
                  </Badge>
                </HStack>
                
                <Text fontWeight="semibold" fontSize="sm" mb={2} noOfLines={2}>
                  {source.video_title}
                </Text>
                
                <Link
                  onClick={() => handleSourceClick(source)}
                  color="blue.500"
                  fontWeight="medium"
                  fontSize="sm"
                  cursor="pointer"
                  _hover={{ textDecoration: 'underline' }}
                  display="flex"
                  alignItems="center"
                  gap={1}
                >
                  <ExternalLinkIcon />
                  Xem tại {formatTime(source.start_time)} - {formatTime(source.end_time)}
                </Link>
                
                {source.text && (
                  <Text
                    fontSize="xs"
                    color="gray.600"
                    mt={2}
                    noOfLines={2}
                    fontStyle="italic"
                  >
                    "{source.text.slice(0, 150)}..."
                  </Text>
                )}
              </Box>
            ))}
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

