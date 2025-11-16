/**
 * QuizDisplay component - Interactive quiz display with validation
 */
import React from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Radio,
  RadioGroup,
  Textarea,
  Spinner,
  Progress,
  Badge,
  Divider,
  Link,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
} from '@chakra-ui/react';
import { CheckCircleIcon, WarningIcon } from '@chakra-ui/icons';
import { Quiz, QuizQuestion } from '../../types';
import { useQuizStore } from '../../stores';

interface QuizDisplayProps {
  quiz: Quiz | null;
  isGenerating: boolean;
  generationProgress: number;
  isValidating: boolean;
  onSubmitAnswers: () => void;
}

export const QuizDisplay: React.FC<QuizDisplayProps> = ({
  quiz,
  isGenerating,
  generationProgress,
  isValidating,
  onSubmitAnswers,
}) => {
  const { userAnswers, setAnswer, validationResults } = useQuizStore();

  // Convert Map to object for RadioGroup controlled component
  const getAnswer = (questionIndex: number): string => {
    return userAnswers.get(questionIndex) || '';
  };

  // Check if all questions are answered
  const allAnswered = quiz?.questions?.every((q) =>
    userAnswers.has(q.question_index)
  ) ?? false;

  // Check if validation is complete
  const validationComplete = quiz?.questions?.every((q) =>
    validationResults.has(q.question_index)
  ) ?? false;

  // Calculate score
  const calculateScore = () => {
    if (!quiz || !quiz.questions || validationResults.size === 0) return null;

    let totalScore = 0;
    let maxScore = quiz.questions.length * 100;

    quiz.questions.forEach((q) => {
      const result = validationResults.get(q.question_index);
      if (!result) return;

      if (q.question_type === 'mcq') {
        totalScore += result.is_correct ? 100 : 0;
      } else {
        totalScore += result.llm_score || 0;
      }
    });

    return Math.round((totalScore / maxScore) * 100);
  };

  // Render MCQ question
  const renderMCQQuestion = (question: QuizQuestion) => {
    const result = validationResults.get(question.question_index);
    const userAnswer = getAnswer(question.question_index);

    return (
      <VStack align="stretch" spacing={3}>
        <RadioGroup
          value={userAnswer}
          onChange={(value) => setAnswer(question.question_index, value)}
          isDisabled={validationComplete}
        >
          <VStack align="stretch" spacing={2}>
            {Object.entries(question.options || {}).map(([key, value]) => {
              const isCorrect = key === question.correct_answer;
              const isUserAnswer = key === userAnswer;

              return (
                <HStack
                  key={key}
                  p={3}
                  borderRadius="md"
                  borderWidth="1px"
                  borderColor={
                    result
                      ? isCorrect
                        ? 'green.300'
                        : isUserAnswer
                        ? 'red.300'
                        : 'gray.200'
                      : 'gray.200'
                  }
                  bg={
                    result
                      ? isCorrect
                        ? 'green.50'
                        : isUserAnswer
                        ? 'red.50'
                        : 'white'
                      : 'white'
                  }
                >
                  <Radio value={key}>{key}</Radio>
                  <Text flex={1}>{value}</Text>
                  {result && isCorrect && (
                    <CheckCircleIcon color="green.500" />
                  )}
                  {result && isUserAnswer && !isCorrect && (
                    <WarningIcon color="red.500" />
                  )}
                </HStack>
              );
            })}
          </VStack>
        </RadioGroup>

        {/* Show validation result */}
        {result && (
          <Alert status={result.is_correct ? 'success' : 'error'} borderRadius="md">
            <AlertIcon />
            <Box flex={1}>
              <AlertTitle>
                {result.is_correct ? 'Correct!' : 'Incorrect'}
              </AlertTitle>
              {result.explanation && (
                <AlertDescription>{result.explanation}</AlertDescription>
              )}
            </Box>
          </Alert>
        )}
      </VStack>
    );
  };

  // Render open-ended question
  const renderOpenEndedQuestion = (question: QuizQuestion) => {
    const result = validationResults.get(question.question_index);
    const userAnswer = getAnswer(question.question_index);

    return (
      <VStack align="stretch" spacing={3}>
        <Textarea
          placeholder="Enter your answer here..."
          value={userAnswer}
          onChange={(e) => setAnswer(question.question_index, e.target.value)}
          isDisabled={validationComplete}
          minH="150px"
        />

        {/* Show validation result AFTER submission */}
        {result && result.llm_feedback && (
          <Alert
            status={
              result.llm_score && result.llm_score >= 70
                ? 'success'
                : result.llm_score && result.llm_score >= 50
                ? 'warning'
                : 'error'
            }
            borderRadius="md"
          >
            <AlertIcon />
            <Box flex={1}>
              <AlertTitle>
                Score: {result.llm_score}/100
              </AlertTitle>
              <AlertDescription>
                {/* 1. Feedback */}
                <Box mt={2}>
                  <Text fontWeight="bold" fontSize="sm" mb={1}>Feedback:</Text>
                  <Text fontSize="sm">{result.llm_feedback.feedback}</Text>
                </Box>

                {/* 2. Reference Answer */}
                {question.reference_answer && (
                  <Box mt={3}>
                    <Text fontWeight="bold" fontSize="sm" mb={1}>Reference Answer:</Text>
                    <Text fontSize="sm">{question.reference_answer}</Text>
                  </Box>
                )}

                {/* 3. Points to Cover */}
                {question.key_points && question.key_points.length > 0 && (
                  <Box mt={3}>
                    <Text fontWeight="bold" fontSize="sm" mb={1}>Points to Cover:</Text>
                    <VStack align="stretch" spacing={1} mt={1}>
                      {question.key_points.map((point, idx) => (
                        <HStack key={idx}>
                          <Text fontSize="sm">• {point}</Text>
                        </HStack>
                      ))}
                    </VStack>
                  </Box>
                )}

                {/* 4. Covered Points */}
                <Box mt={3}>
                  <Text fontWeight="bold" fontSize="sm" color="green.600" mb={1}>
                    Covered Points:
                  </Text>
                  {result.llm_feedback.covered_points.length > 0 ? (
                    <VStack align="stretch" spacing={1} mt={1}>
                      {result.llm_feedback.covered_points.map((point, idx) => (
                        <HStack key={idx}>
                          <CheckCircleIcon color="green.500" boxSize={3} />
                          <Text fontSize="sm">{point}</Text>
                        </HStack>
                      ))}
                    </VStack>
                  ) : (
                    <Text fontSize="sm" color="gray.600">None</Text>
                  )}
                </Box>

                {/* 5. Missing Points */}
                <Box mt={3}>
                  <Text fontWeight="bold" fontSize="sm" color="red.600" mb={1}>
                    Missing Points:
                  </Text>
                  {result.llm_feedback.missing_points.length > 0 ? (
                    <VStack align="stretch" spacing={1} mt={1}>
                      {result.llm_feedback.missing_points.map((point, idx) => (
                        <HStack key={idx}>
                          <WarningIcon color="red.500" boxSize={3} />
                          <Text fontSize="sm">{point}</Text>
                        </HStack>
                      ))}
                    </VStack>
                  ) : (
                    <Text fontSize="sm" color="gray.600">None</Text>
                  )}
                </Box>
              </AlertDescription>
            </Box>
          </Alert>
        )}
      </VStack>
    );
  };

  // Render video source
  const renderVideoSource = (question: QuizQuestion) => {
    if (!question.video_id || !question.video_url) return null;

    const timestamp = question.timestamp || 0;
    const videoUrl = `${question.video_url}&t=${timestamp}s`;

    return (
      <HStack spacing={2} fontSize="sm" color="gray.600">
        <Text fontWeight="medium">Source:</Text>
        <Link href={videoUrl} isExternal color="blue.500">
          {question.video_title}
        </Link>
        <Text>({Math.floor(timestamp / 60)}:{String(timestamp % 60).padStart(2, '0')})</Text>
      </HStack>
    );
  };

  // Show generation progress
  if (isGenerating) {
    return (
      <Box
        flex={1}
        w="full"
        h="full"
        display="flex"
        alignItems="center"
        justifyContent="center"
        p={6}
      >
        <VStack spacing={4}>
          <Spinner size="xl" color="blue.500" />
          <Text fontSize="lg" fontWeight="medium">
            {generationProgress === 0 ? 'Starting quiz generation...' : 'Generating quiz...'}
          </Text>
          {generationProgress > 0 && (
            <>
              <Progress
                value={generationProgress}
                w="300px"
                borderRadius="md"
                colorScheme="blue"
              />
              <Text fontSize="sm" color="gray.600">
                {generationProgress}%
              </Text>
            </>
          )}
        </VStack>
      </Box>
    );
  }

  // Show message if no quiz or quiz has no questions (partial/corrupted data)
  if (!quiz || !quiz.questions || quiz.questions.length === 0) {
    return (
      <Box
        flex={1}
        w="full"
        h="full"
        display="flex"
        alignItems="center"
        justifyContent="center"
        p={6}
      >
        <Text fontSize="lg" color="gray.500">
          Generate a quiz to get started
        </Text>
      </Box>
    );
  }

  const score = calculateScore();

  return (
    <Box
      flex={1}
      w="full"
      h="full"
      overflowY="auto"
      overflowX="hidden"
      p={6}
      bg="white"
    >
      <VStack spacing={6} align="stretch" maxW="800px" mx="auto">
        {/* Quiz Header */}
        <Box>
          <HStack justify="space-between" mb={2}>
            <Text fontSize="2xl" fontWeight="bold">
              {quiz.topic || 'Quiz'}
            </Text>
            <Badge colorScheme="blue" fontSize="md" px={3} py={1}>
              {quiz.num_questions} Questions
            </Badge>
          </HStack>
          {quiz.chapters && quiz.chapters.length > 0 && (
            <HStack spacing={2}>
              <Text fontSize="sm" color="gray.600">
                Chapters:
              </Text>
              {quiz.chapters.map((chapter) => (
                <Badge key={chapter} colorScheme="purple">
                  {chapter}
                </Badge>
              ))}
            </HStack>
          )}
        </Box>

        <Divider />

        {/* Score Display (after validation) */}
        {validationComplete && score !== null && (
          <Alert
            status={score >= 70 ? 'success' : score >= 50 ? 'warning' : 'error'}
            borderRadius="md"
          >
            <AlertIcon />
            <Box>
              <AlertTitle>Quiz Complete!</AlertTitle>
              <AlertDescription>
                Your score: {score}% ({validationResults.size}/{quiz.num_questions} questions)
              </AlertDescription>
            </Box>
          </Alert>
        )}

        {/* Questions */}
        {quiz.questions.map((question, idx) => {
          const result = validationResults.get(question.question_index);
          const questionScore = result
            ? question.question_type === 'mcq'
              ? result.is_correct ? 100 : 0
              : result.llm_score || 0
            : null;

          return (
            <Box
              key={question.id}
              p={5}
              borderWidth="1px"
              borderRadius="lg"
              borderColor="gray.200"
              bg="gray.50"
            >
              <VStack align="stretch" spacing={4}>
                {/* Question Header */}
                <HStack justify="space-between">
                  <HStack spacing={2}>
                    <Text fontSize="lg" fontWeight="semibold">
                      Question {idx + 1}
                    </Text>
                    {questionScore !== null && (
                      <Badge
                        colorScheme={
                          questionScore >= 70
                            ? 'green'
                            : questionScore >= 50
                            ? 'yellow'
                            : 'red'
                        }
                        fontSize="md"
                        px={2}
                      >
                        {questionScore}/100
                      </Badge>
                    )}
                  </HStack>
                  <Badge colorScheme={question.question_type === 'mcq' ? 'blue' : 'green'}>
                    {question.question_type === 'mcq' ? 'Multiple Choice' : 'Open-ended'}
                  </Badge>
                </HStack>

                {/* Question Text */}
                <Text fontSize="md">{question.question}</Text>

                {/* Answer Input */}
                {question.question_type === 'mcq'
                  ? renderMCQQuestion(question)
                  : renderOpenEndedQuestion(question)}

                {/* Video Source (show after validation) */}
                {validationComplete && renderVideoSource(question)}
              </VStack>
            </Box>
          );
        })}

        {/* Submit Button */}
        {!validationComplete && (
          <Button
            colorScheme="blue"
            size="lg"
            onClick={onSubmitAnswers}
            isLoading={isValidating}
            loadingText="Validating..."
            isDisabled={!allAnswered || isValidating}
          >
            Submit Answers
          </Button>
        )}

        {/* Validation Progress */}
        {isValidating && !validationComplete && (
          <Box>
            <Text fontSize="sm" color="gray.600" mb={2}>
              Validating answers... ({validationResults.size}/{quiz.num_questions})
            </Text>
            <Progress
              value={(validationResults.size / quiz.num_questions) * 100}
              borderRadius="md"
              colorScheme="blue"
            />
          </Box>
        )}
      </VStack>
    </Box>
  );
};
