/**
 * SessionItem - Individual session in sidebar
 */
import React from 'react';
import { Box, HStack, Text, IconButton, useColorModeValue } from '@chakra-ui/react';
import { DeleteIcon } from '@chakra-ui/icons';
import { ChatSession } from '../../types';

interface SessionItemProps {
  session: ChatSession;
  isActive: boolean;
  colorScheme?: string;
  onClick: () => void;
  onDelete: (e: React.MouseEvent) => void;
}

export const SessionItem: React.FC<SessionItemProps> = ({
  session,
  isActive,
  colorScheme = 'blue',
  onClick,
  onDelete,
}) => {
  return (
    <HStack
      px={3}
      py={2}
      cursor="pointer"
      onClick={onClick}
      bg={isActive ? `${colorScheme}.50` : 'transparent'}
      _hover={{ bg: isActive ? `${colorScheme}.100` : useColorModeValue('gray.100', 'gray.800') }}
      borderRadius="md"
      spacing={2}
      justify="space-between"
    >
      <Box flex={1} overflow="hidden">
        <Text
          fontSize="sm"
          fontWeight={isActive ? 'bold' : 'medium'}
          noOfLines={2}
          color={isActive ? `${colorScheme}.700` : useColorModeValue('gray.800', 'gray.200')}
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

