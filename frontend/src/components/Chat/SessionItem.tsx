/**
 * SessionItem - Individual session in sidebar
 */
import React from 'react';
import { Box, HStack, Text, IconButton } from '@chakra-ui/react';
import { DeleteIcon } from '@chakra-ui/icons';
import { ChatSession } from '../../types';

interface SessionItemProps {
  session: ChatSession;
  isActive: boolean;
  onClick: () => void;
  onDelete: (e: React.MouseEvent) => void;
}

export const SessionItem: React.FC<SessionItemProps> = ({
  session,
  isActive,
  onClick,
  onDelete,
}) => {
  return (
    <HStack
      px={3}
      py={2}
      cursor="pointer"
      onClick={onClick}
      bg={isActive ? 'blue.50' : 'transparent'}
      _hover={{ bg: isActive ? 'blue.100' : 'gray.50' }}
      borderRadius="md"
      spacing={2}
      justify="space-between"
    >
      <Box flex={1} overflow="hidden">
        <Text
          fontSize="sm"
          fontWeight={isActive ? 'semibold' : 'normal'}
          noOfLines={2}
          color={isActive ? 'blue.700' : 'gray.700'}
        >
          {session.title || 'Untitled Session'}
        </Text>
      </Box>
      
      <IconButton
        icon={<DeleteIcon />}
        size="xs"
        variant="ghost"
        colorScheme="red"
        aria-label="Delete session"
        onClick={onDelete}
        opacity={0.6}
        _hover={{ opacity: 1 }}
      />
    </HStack>
  );
};

