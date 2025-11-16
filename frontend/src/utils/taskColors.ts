/**
 * Utility for managing task-specific color themes
 */
import { TaskType } from '../types';

export const TASK_COLORS: Record<TaskType, string> = {
  text_summary: 'blue',
  qa: 'green',
  video_summary: 'orange',
  quiz: 'purple',
};

/**
 * Get the color scheme for a given task type
 */
export const getTaskColor = (taskType: TaskType): string => {
  return TASK_COLORS[taskType] || 'blue';
};
