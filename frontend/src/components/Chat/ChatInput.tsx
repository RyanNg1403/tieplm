/**
 * ChatInput component with mode switcher and chapter filter
 */
import React, { useState, useEffect } from 'react';
import {
  HStack,
  Input,
  Button,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  IconButton,
  Checkbox,
  VStack,
  Text,
  Select,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  useColorModeValue,
} from '@chakra-ui/react';
import { ChevronDownIcon, SettingsIcon, RepeatIcon } from '@chakra-ui/icons';
import { TaskType } from '../../types';
import { chaptersAPI, videoSummaryAPI, type VideoInfo } from '../../services/api';

interface ChatInputProps {
  currentMode: TaskType;
  colorScheme?: string;
  onModeChange: (mode: TaskType) => void;
  onSend: (message: string) => void;
  isStreaming: boolean;
  selectedChapters: string[];
  onChaptersChange: (chapters: string[]) => void;
  selectedVideo: string | null;
  onVideoChange: (videoId: string | null) => void;
  // Quiz-specific props
  quizQuestionType?: string;
  onQuizQuestionTypeChange?: (type: string) => void;
  quizNumQuestions?: number;
  onQuizNumQuestionsChange?: (num: number) => void;
}

const MODE_LABELS: Record<TaskType, string> = {
  text_summary: 'Text Summary',
  qa: 'Q&A',
  video_summary: 'Video Summary',
  quiz: 'Quiz',
};

export const ChatInput: React.FC<ChatInputProps> = ({
  currentMode,
  colorScheme = 'blue',
  onModeChange,
  onSend,
  isStreaming,
  selectedChapters,
  onChaptersChange,
  selectedVideo,
  onVideoChange,
  quizQuestionType = 'mcq',
  onQuizQuestionTypeChange,
  quizNumQuestions = 5,
  onQuizNumQuestionsChange,
}) => {
  const [input, setInput] = useState('');
  const [videos, setVideos] = useState<VideoInfo[]>([]);
  const [loadingVideos, setLoadingVideos] = useState(false);
  
  // Get available chapters (hardcoded from chapters_urls.json ground truth)
  const availableChapters = chaptersAPI.getChapters();
  
  // Load videos when video_summary mode is active
  useEffect(() => {
    if (currentMode === 'video_summary' && videos.length === 0) {
      setLoadingVideos(true);
      videoSummaryAPI.getVideos()
        .then((list) => {
          // Sort by chapter then title using localeCompare for correct Vietnamese ordering
          list.sort((a, b) => {
            const chapterCompare = a.chapter.localeCompare(b.chapter, 'vi');
            return chapterCompare !== 0 ? chapterCompare : a.title.localeCompare(b.title, 'vi');
          });
          setVideos(list);
        })
        .catch(console.error)
        .finally(() => setLoadingVideos(false));
    }
  }, [currentMode, videos.length]);
  
  const handleSend = () => {
    if (currentMode === 'video_summary') {
      // For video_summary, send button triggers summarization
      if (selectedVideo && !isStreaming) {
        onSend('__VIDEO_SUMMARY_REGENERATE__'); // Special marker to skip user message
      }
    } else if (currentMode === 'quiz') {
      // For quiz, send button triggers quiz generation
      if (!isStreaming) {
        // Pass the query (optional) via the onSend handler
        onSend(input.trim() || '__QUIZ_GENERATE__');
        setInput('');
      }
    } else if (input.trim() && !isStreaming) {
      onSend(input.trim());
      setInput('');
    }
  };
  
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };
  
  const handleChapterToggle = (chapter: string) => {
    if (selectedChapters.includes(chapter)) {
      onChaptersChange(selectedChapters.filter(c => c !== chapter));
    } else {
      onChaptersChange([...selectedChapters, chapter]);
    }
  };
  
  return (
    <HStack
      p={4}
      borderTop="1px"
      borderColor={useColorModeValue('gray.200', 'gray.700')}
      bg={useColorModeValue('white', 'gray.800')}
      spacing={2}
    >
      {/* Mode Switcher */}
      <Menu>
        <MenuButton
          as={Button}
          rightIcon={<ChevronDownIcon />}
          size="md"
          minW="180px"
        >
          {MODE_LABELS[currentMode]}
        </MenuButton>
        <MenuList>
          {Object.entries(MODE_LABELS).map(([mode, label]) => (
            <MenuItem
              key={mode}
              onClick={() => onModeChange(mode as TaskType)}
              fontWeight={mode === currentMode ? 'bold' : 'normal'}
            >
              {label}
            </MenuItem>
          ))}
        </MenuList>
      </Menu>
      
      {/* Chapter Filter (for text_summary, qa, and quiz) */}
      {(currentMode === 'text_summary' || currentMode === 'qa' || currentMode === 'quiz') && (
        <Menu closeOnSelect={false}>
          <MenuButton
            as={IconButton}
            icon={<SettingsIcon />}
            variant={selectedChapters.length > 0 ? 'solid' : 'outline'}
            colorScheme={selectedChapters.length > 0 ? colorScheme : 'gray'}
            size="md"
            aria-label="Filter chapters"
          />
          <MenuList maxH="300px" overflowY="auto">
            <VStack align="stretch" spacing={1} p={2}>
              <Text fontWeight="bold" fontSize="sm" px={2}>
                Chọn chương:
              </Text>
              {selectedChapters.length > 0 && (
                <Button
                  size="xs"
                  variant="ghost"
                  onClick={() => onChaptersChange([])}
                  colorScheme="red"
                >
                  Clear all
                </Button>
              )}
              {availableChapters.map((chapter) => (
                <Checkbox
                  key={chapter}
                  isChecked={selectedChapters.includes(chapter)}
                  onChange={() => handleChapterToggle(chapter)}
                  px={2}
                >
                  {chapter}
                </Checkbox>
              ))}
            </VStack>
          </MenuList>
        </Menu>
      )}

      {/* Quiz Options (for quiz mode) */}
      {currentMode === 'quiz' && (
        <>
          <Select
            value={quizQuestionType}
            onChange={(e) => onQuizQuestionTypeChange?.(e.target.value)}
            disabled={isStreaming}
            size="md"
            minW="140px"
          >
            <option value="mcq">MCQ</option>
            <option value="open_ended">Open-ended</option>
            <option value="mixed">Mixed</option>
          </Select>
          <NumberInput
            value={quizNumQuestions}
            onChange={(_, value) => onQuizNumQuestionsChange?.(isNaN(value) ? 5 : value)}
            min={1}
            max={20}
            size="md"
            minW="100px"
            isDisabled={isStreaming}
          >
            <NumberInputField />
            <NumberInputStepper>
              <NumberIncrementStepper />
              <NumberDecrementStepper />
            </NumberInputStepper>
          </NumberInput>
        </>
      )}
      
      {/* Video Selection (for video_summary) */}
      {currentMode === 'video_summary' && (
        <Select
          placeholder="Select a video..."
          value={selectedVideo || ''}
          onChange={(e) => onVideoChange(e.target.value || null)}
          disabled={isStreaming || loadingVideos}
          size="md"
          flex={1}
        >
          {videos.map((video) => (
            <option key={video.id} value={video.id}>
              {video.title}
            </option>
          ))}
        </Select>
      )}
      
      {/* Input Field (for text_summary, qa, and quiz) */}
      {(currentMode === 'text_summary' || currentMode === 'qa' || currentMode === 'quiz') && (
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={
            currentMode === 'text_summary' || currentMode === 'quiz'
              ? 'Enter topic or question (e.g., "ResNet architecture")...'
              : 'Type your message...'
          }
          size="md"
          disabled={isStreaming}
        />
      )}
      
      {/* Send/Regenerate/Generate Button */}
      <Button
        onClick={handleSend}
        colorScheme={colorScheme}
        size="md"
        isLoading={isStreaming}
        disabled={
          currentMode === 'video_summary'
            ? !selectedVideo || isStreaming
            : currentMode === 'quiz'
            ? isStreaming
            : !input.trim() || isStreaming
        }
        leftIcon={currentMode === 'video_summary' ? <RepeatIcon /> : undefined}
        minW={currentMode === 'quiz' ? '140px' : undefined}
        px={currentMode === 'quiz' ? 6 : undefined}
      >
        {currentMode === 'video_summary'
          ? 'Regenerate'
          : currentMode === 'quiz'
          ? 'Generate Quiz'
          : 'Send'}
      </Button>
    </HStack>
  );
};

