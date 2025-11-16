/**
 * Sidebar - Chat history sidebar (ChatGPT-style)
 */
import React from 'react';
import {
  Box,
  VStack,
  Button,
  Text,
  Divider,
  Spinner,
  Center,
  useColorModeValue,
} from '@chakra-ui/react';
import { AddIcon } from '@chakra-ui/icons';
import { useQuery } from '@tanstack/react-query';
import { SessionItem } from './SessionItem';
import { sessionsAPI, quizAPI, QuizHistory } from '../../services/api';
import { ChatSession, TaskType } from '../../types';

interface SidebarProps {
  currentSessionId: string | null;
  taskType?: TaskType; // Filter sessions by task type
  colorScheme?: string; // Theme color for the task
  onNewChat: () => void;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentSessionId,
  taskType,
  colorScheme = 'blue',
  onNewChat,
  onSelectSession,
  onDeleteSession,
}) => {
  // Fetch sessions or quiz history based on task type
  const { data: sessions = [], isLoading, refetch } = useQuery({
    queryKey: ['sessions', taskType],
    queryFn: async () => {
      if (taskType === 'quiz') {
        // Fetch quiz history and convert to session format
        const quizzes = await quizAPI.getQuizHistory();
        return quizzes.map((quiz: QuizHistory) => ({
          id: quiz.id,
          title: quiz.topic || `Quiz ${quiz.num_questions} câu (${quiz.question_type})`,
          created_at: quiz.created_at,
          updated_at: quiz.created_at,
        })) as ChatSession[];
      } else {
        // Fetch chat sessions
        return sessionsAPI.getSessions('default_user', taskType);
      }
    },
    refetchInterval: 30000, // Refetch every 30s
  });

  const handleDelete = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (window.confirm('Delete this conversation?')) {
      onDeleteSession(sessionId);
      refetch(); // Refresh list after delete
    }
  };

  // Get button text based on task type
  const getNewButtonText = () => {
    switch (taskType) {
      case 'quiz':
        return 'New Quiz';
      case 'video_summary':
        return 'New Video';
      default:
        return 'New Chat';
    }
  };

  // Group sessions by date
  const groupedSessions = React.useMemo(() => {
    const groups: {
      today: ChatSession[];
      yesterday: ChatSession[];
      older: ChatSession[];
    } = {
      today: [],
      yesterday: [],
      older: [],
    };

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    sessions.forEach((session) => {
      const sessionDate = new Date(session.created_at);
      const sessionDay = new Date(
        sessionDate.getFullYear(),
        sessionDate.getMonth(),
        sessionDate.getDate()
      );

      if (sessionDay.getTime() === today.getTime()) {
        groups.today.push(session);
      } else if (sessionDay.getTime() === yesterday.getTime()) {
        groups.yesterday.push(session);
      } else {
        groups.older.push(session);
      }
    });

    return groups;
  }, [sessions]);

  return (
    <Box
      w="280px"
      h="100vh"
      bg={useColorModeValue('gray.50', 'gray.900')}
      borderRight="1px"
      borderColor={useColorModeValue('gray.200', 'gray.700')}
      display="flex"
      flexDirection="column"
    >
      {/* Header */}
      <Box p={3} borderBottom="1px" borderColor={useColorModeValue('gray.200', 'gray.700')}>
        <Button
          leftIcon={<AddIcon />}
          colorScheme={colorScheme}
          size="sm"
          w="full"
          onClick={onNewChat}
        >
          {getNewButtonText()}
        </Button>
      </Box>

      {/* Sessions List */}
      <Box flex={1} overflowY="auto" p={2}>
        {isLoading ? (
          <Center h="200px">
            <Spinner />
          </Center>
        ) : sessions.length === 0 ? (
          <Center h="200px">
            <Text fontSize="sm" color={useColorModeValue('gray.500', 'gray.400')}>
              No conversations yet
            </Text>
          </Center>
        ) : (
          <VStack align="stretch" spacing={4}>
            {/* Today */}
            {groupedSessions.today.length > 0 && (
              <Box>
                <Text
                  fontSize="xs"
                  fontWeight="bold"
                  color={useColorModeValue('gray.500', 'gray.400')}
                  mb={2}
                  px={2}
                >
                  Today
                </Text>
                <VStack align="stretch" spacing={1}>
                  {groupedSessions.today.map((session) => (
                    <SessionItem
                      key={session.id}
                      session={session}
                      isActive={session.id === currentSessionId}
                      colorScheme={colorScheme}
                      onClick={() => onSelectSession(session.id)}
                      onDelete={(e) => handleDelete(e, session.id)}
                    />
                  ))}
                </VStack>
              </Box>
            )}

            {/* Yesterday */}
            {groupedSessions.yesterday.length > 0 && (
              <Box>
                {groupedSessions.today.length > 0 && <Divider />}
                <Text
                  fontSize="xs"
                  fontWeight="bold"
                  color={useColorModeValue('gray.500', 'gray.400')}
                  mb={2}
                  px={2}
                  mt={2}
                >
                  Yesterday
                </Text>
                <VStack align="stretch" spacing={1}>
                  {groupedSessions.yesterday.map((session) => (
                    <SessionItem
                      key={session.id}
                      session={session}
                      isActive={session.id === currentSessionId}
                      colorScheme={colorScheme}
                      onClick={() => onSelectSession(session.id)}
                      onDelete={(e) => handleDelete(e, session.id)}
                    />
                  ))}
                </VStack>
              </Box>
            )}

            {/* Older */}
            {groupedSessions.older.length > 0 && (
              <Box>
                {(groupedSessions.today.length > 0 ||
                  groupedSessions.yesterday.length > 0) && <Divider />}
                <Text
                  fontSize="xs"
                  fontWeight="bold"
                  color={useColorModeValue('gray.500', 'gray.400')}
                  mb={2}
                  px={2}
                  mt={2}
                >
                  Older
                </Text>
                <VStack align="stretch" spacing={1}>
                  {groupedSessions.older.map((session) => (
                    <SessionItem
                      key={session.id}
                      session={session}
                      isActive={session.id === currentSessionId}
                      colorScheme={colorScheme}
                      onClick={() => onSelectSession(session.id)}
                      onDelete={(e) => handleDelete(e, session.id)}
                    />
                  ))}
                </VStack>
              </Box>
            )}
          </VStack>
        )}
      </Box>

      {/* Footer */}
      <Box p={3} borderTop="1px" borderColor="gray.200">
        <Text fontSize="xs" color="gray.500" textAlign="center">
          CS431 Deep Learning Assistant
        </Text>
      </Box>
    </Box>
  );
};

