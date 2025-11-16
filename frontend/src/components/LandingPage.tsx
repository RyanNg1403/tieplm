/**
 * Landing Page component with task selection cards
 * Inspired by Podia's landing page design
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  VStack,
  HStack,
  Heading,
  Text,
  Button,
  Container,
  SimpleGrid,
  Card,
  CardBody,
  Icon,
  Image,
  useColorModeValue,
} from '@chakra-ui/react';
import { ArrowForwardIcon } from '@chakra-ui/icons';
import { TaskType } from '../types';
import { useChatStore } from '../stores/chatStore';
import { ColorModeSwitcher } from './ColorModeSwitcher';

// Import circular images
import textSumImage from '@/assets/images/tiepLM_text_sum-circular.png';
import qaImage from '@/assets/images/tiepLM_qa-circular.png';
import vidSumImage from '@/assets/images/tiepLM_vid_sum-circular.png';
import quizImage from '@/assets/images/tiepLM_quiz-circular.png';

const TASK_INFO: Record<TaskType, { title: string; description: string; color: string; image: string }> = {
  text_summary: {
    title: 'Text Summary',
    description: 'Generate hierarchical summaries from video transcripts with inline citations and source references.',
    color: 'blue',
    image: textSumImage,
  },
  qa: {
    title: 'Q&A',
    description: 'Ask questions about the course content and get accurate answers with citations to relevant video segments.',
    color: 'green',
    image: qaImage,
  },
  video_summary: {
    title: 'Video Summary',
    description: 'Get timestamp-based video summaries that help you navigate and understand video content efficiently.',
    color: 'orange',
    image: vidSumImage,
  },
  quiz: {
    title: 'Quiz',
    description: 'Auto-generate quizzes from course material to test your understanding and reinforce learning.',
    color: 'purple',
    image: quizImage,
  },
};

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { setMode } = useChatStore();
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const textColor = useColorModeValue('gray.800', 'white');

  const handleTaskSelect = (taskType: TaskType) => {
    setMode(taskType);
    // Navigate to chat route
    navigate('/chat');
  };

  return (
    <Box
      minH="100vh"
      bg={bgColor}
      position="relative"
      overflow="hidden"
    >
      {/* Color Mode Switcher */}
      <ColorModeSwitcher position="fixed" />
      {/* Decorative shapes */}
      <Box
        position="absolute"
        top="10%"
        left="5%"
        w="100px"
        h="100px"
        bg="blue.200"
        borderRadius="full"
        opacity={0.3}
        zIndex={0}
      />
      <Box
        position="absolute"
        top="20%"
        right="10%"
        w="80px"
        h="80px"
        bg="orange.200"
        borderRadius="20px"
        transform="rotate(45deg)"
        opacity={0.3}
        zIndex={0}
      />
      <Box
        position="absolute"
        bottom="20%"
        left="10%"
        w="120px"
        h="120px"
        bg="purple.200"
        borderRadius="30px"
        transform="rotate(-30deg)"
        opacity={0.3}
        zIndex={0}
      />
      <Box
        position="absolute"
        bottom="15%"
        right="8%"
        w="90px"
        h="90px"
        bg="green.200"
        borderRadius="full"
        opacity={0.3}
        zIndex={0}
      />

      <Container maxW="7xl" py={12} position="relative" zIndex={1}>
        <VStack spacing={8} align="stretch">
          {/* Header Section */}
          <VStack spacing={4} textAlign="center" py={8}>
            <Heading
              as="h1"
              size="2xl"
              fontWeight="bold"
              color={textColor}
              lineHeight="1.2"
            >
              TiepLM: One-for-all AI Assistant
            </Heading>
            <Text
              fontSize="xl"
              color={useColorModeValue('gray.600', 'gray.300')}
              maxW="2xl"
              mx="auto"
            >
              An AI assistant which makes you feel like <strong>Ph.D. Vinh-Tiep Nguyen</strong> is always there for you in CS431.
            </Text>
            <Text
              fontSize="md"
              color={useColorModeValue('gray.500', 'gray.400')}
              maxW="xl"
              mx="auto"
            >
              TiepLM is All You Need in CS431.
            </Text>
          </VStack>

          {/* Task Cards Grid */}
          <SimpleGrid
            columns={{ base: 1, md: 2, lg: 4 }}
            spacing={6}
            mt={12}
          >
            {(Object.entries(TASK_INFO) as [TaskType, typeof TASK_INFO[TaskType]][])
              .map(([taskType, info], index) => {
                // Create slight rotation for visual interest (like Podia)
                const rotation = index % 2 === 0 ? '2deg' : '-2deg';

                // Dark mode colors - darker shades for better contrast
                const cardBg = useColorModeValue(`${info.color}.50`, `${info.color}.800`);
                const cardBorder = useColorModeValue(`${info.color}.200`, `${info.color}.700`);
                const titleColor = useColorModeValue(`${info.color}.700`, `${info.color}.100`);
                const descColor = useColorModeValue('gray.700', 'white');
                const iconColor = useColorModeValue(`${info.color}.600`, `${info.color}.200`);
                const imageBorder = useColorModeValue(`${info.color}.300`, `${info.color}.400`);

                return (
                  <Card
                    key={taskType}
                    bg={cardBg}
                    borderRadius="2xl"
                    overflow="hidden"
                    cursor="pointer"
                    transition="all 0.3s ease"
                    _hover={{
                      transform: `translateY(-12px) rotate(${rotation})`,
                      boxShadow: '2xl',
                    }}
                    onClick={() => handleTaskSelect(taskType)}
                    position="relative"
                    minH="300px"
                    transform={`rotate(${rotation})`}
                    borderWidth="1px"
                    borderColor={cardBorder}
                  >
                    <CardBody p={6} display="flex" flexDirection="column">
                      {/* Circular Image */}
                      <Box display="flex" justifyContent="center" mb={4}>
                        <Image
                          src={info.image}
                          alt={info.title}
                          boxSize="100px"
                          objectFit="cover"
                          borderRadius="full"
                          border={`3px solid`}
                          borderColor={imageBorder}
                          boxShadow="md"
                        />
                      </Box>

                      <HStack justify="space-between" mb={4}>
                        <Heading
                          as="h3"
                          size="lg"
                          color={titleColor}
                          fontWeight="bold"
                        >
                          {info.title}
                        </Heading>
                        <Icon
                          as={ArrowForwardIcon}
                          w={6}
                          h={6}
                          color={iconColor}
                        />
                      </HStack>
                      <Text
                        color={descColor}
                        fontSize="sm"
                        lineHeight="1.7"
                        flex={1}
                        mb={4}
                      >
                        {info.description}
                      </Text>
                      <Button
                        mt="auto"
                        colorScheme={info.color}
                        size="md"
                        rightIcon={<ArrowForwardIcon />}
                        alignSelf="flex-start"
                        fontWeight="semibold"
                      >
                        Get Started
                      </Button>
                    </CardBody>
                  </Card>
                );
              })}
          </SimpleGrid>
        </VStack>
      </Container>
    </Box>
  );
};

