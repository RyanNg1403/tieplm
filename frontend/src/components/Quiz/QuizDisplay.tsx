/**
 * Component to display quiz questions in a formatted way
 */
import React from 'react';
import {
    VStack,
    Box,
    Text,
    HStack,
    Badge,
    Divider,
    Code,
} from '@chakra-ui/react';
import { QuizQuestion } from '../../services/api';

interface QuizDisplayProps {
    questions: QuizQuestion[];
}

export const QuizDisplay: React.FC<QuizDisplayProps> = ({ questions }) => {
    if (!questions || questions.length === 0) {
        return (
            <Box p={4} textAlign="center" color="gray.500">
                No questions available
            </Box>
        );
    }

    return (
        <VStack align="stretch" spacing={4} p={4}>
            <Box>
                <Text fontSize="xl" fontWeight="bold" mb={2}>
                    Quiz Questions ({questions.length})
                </Text>
            </Box>

            {questions.map((question, index) => (
                <Box
                    key={index}
                    border="1px"
                    borderColor="gray.200"
                    borderRadius="md"
                    p={4}
                    bg="white"
                    boxShadow="sm"
                >
                    <VStack align="stretch" spacing={3}>
                        {/* Question Header */}
                        <HStack justify="space-between" align="flex-start">
                            <HStack spacing={2}>
                                <Badge colorScheme="blue" fontSize="sm">
                                    Question {index + 1}
                                </Badge>
                                <Badge
                                    colorScheme={
                                        question.question_type === 'mcq'
                                            ? 'green'
                                            : question.question_type === 'open_ended'
                                                ? 'purple'
                                                : 'orange'
                                    }
                                    fontSize="xs"
                                >
                                    {question.question_type === 'mcq'
                                        ? 'MCQ'
                                        : question.question_type === 'open_ended'
                                            ? 'Open-ended'
                                            : 'Mixed'}
                                </Badge>
                            </HStack>
                        </HStack>

                        {/* Question Text */}
                        <Text fontSize="md" fontWeight="medium" color="gray.800">
                            {question.question}
                        </Text>

                        {/* MCQ Options */}
                        {question.question_type === 'mcq' && question.options && (
                            <VStack align="stretch" spacing={2} pl={4}>
                                {['A', 'B', 'C', 'D'].map((optionLabel, _) => {
                                    const option = question.options?.[optionLabel as keyof typeof question.options];
                                    const isCorrect = question.correct_answer === optionLabel;
                                    return (
                                        <HStack
                                            key={optionLabel}
                                            spacing={2}
                                            p={2}
                                            bg={isCorrect ? 'green.50' : 'gray.50'}
                                            borderRadius="md"
                                            border={isCorrect ? '1px' : '1px'}
                                            borderColor={isCorrect ? 'green.200' : 'gray.200'}
                                        >
                                            <Badge
                                                colorScheme={isCorrect ? 'green' : 'gray'}
                                                minW="24px"
                                                textAlign="center"
                                            >
                                                {optionLabel}
                                            </Badge>
                                            <Text flex={1} fontSize="sm">
                                                {option}
                                            </Text>
                                            {isCorrect && (
                                                <Badge colorScheme="green" fontSize="xs">
                                                    Correct
                                                </Badge>
                                            )}
                                        </HStack>
                                    );
                                })}
                            </VStack>
                        )}

                        {/* Explanation */}
                        {question.explanation && (
                            <Box
                                p={3}
                                bg="blue.50"
                                borderRadius="md"
                                borderLeft="4px"
                                borderColor="blue.400"
                            >
                                <Text fontSize="sm" fontWeight="semibold" color="blue.800" mb={1}>
                                    Explanation:
                                </Text>
                                <Text fontSize="sm" color="blue.700">
                                    {question.explanation}
                                </Text>
                            </Box>
                        )}

                        {/* Video URL if available */}
                        {(question as any).video_url && (
                            <Box>
                                <Text fontSize="xs" color="gray.500">
                                    Source: <Code fontSize="xs">{(question as any).video_url}</Code>
                                </Text>
                            </Box>
                        )}
                    </VStack>

                    {index < questions.length - 1 && <Divider mt={4} />}
                </Box>
            ))}
        </VStack>
    );
};

