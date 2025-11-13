/**
 * ChatInput component with mode switcher and chapter filter
 */
import React, { useState } from 'react';
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
} from '@chakra-ui/react';
import { ChevronDownIcon, SettingsIcon } from '@chakra-ui/icons';
import { TaskType } from '../../types';
import { chaptersAPI } from '../../services/api';

interface ChatInputProps {
  currentMode: TaskType;
  onModeChange: (mode: TaskType) => void;
  onSend: (message: string) => void;
  isStreaming: boolean;
  selectedChapters: string[];
  onChaptersChange: (chapters: string[]) => void;
}

const MODE_LABELS: Record<TaskType, string> = {
  text_summary: 'Text Summary',
  qa: 'Q&A',
  video_summary: 'Video Summary',
  quiz: 'Quiz',
};

export const ChatInput: React.FC<ChatInputProps> = ({
  currentMode,
  onModeChange,
  onSend,
  isStreaming,
  selectedChapters,
  onChaptersChange,
}) => {
  const [input, setInput] = useState('');
  
  // Get available chapters (hardcoded from chapters_urls.json ground truth)
  const availableChapters = chaptersAPI.getChapters();
  
  const handleSend = () => {
    if (input.trim() && !isStreaming) {
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
      borderColor="gray.200"
      bg="white"
      spacing={2}
    >
      {/* Mode Switcher */}
      <Menu>
        <MenuButton
          as={Button}
          rightIcon={<ChevronDownIcon />}
          size="md"
          minW="150px"
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
      
      {/* Chapter Filter (only for text_summary) */}
      {currentMode === 'text_summary' && (
        <Menu closeOnSelect={false}>
          <MenuButton
            as={IconButton}
            icon={<SettingsIcon />}
            variant={selectedChapters.length > 0 ? 'solid' : 'outline'}
            colorScheme={selectedChapters.length > 0 ? 'blue' : 'gray'}
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
      
      {/* Input Field */}
      <Input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder={
          currentMode === 'text_summary'
            ? 'Enter topic or question (e.g., "ResNet architecture")...'
            : 'Type your message...'
        }
        size="md"
        disabled={isStreaming}
      />
      
      {/* Send Button */}
      <Button
        onClick={handleSend}
        colorScheme="blue"
        size="md"
        isLoading={isStreaming}
        disabled={!input.trim() || isStreaming}
      >
        Send
      </Button>
    </HStack>
  );
};

