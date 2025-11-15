/**
 * Custom hook for Server-Sent Events (SSE) streaming
 */
import { useState, useCallback, useRef } from 'react';
import { SSEEvent, SourceReference } from '../types';

interface UseSSEOptions {
  onToken?: (token: string) => void;
  onSources?: (sources: SourceReference[]) => void;
  onDone?: (content: string, sources: SourceReference[], sessionId?: string) => void;
  onError?: (error: string) => void;
  onProgress?: (progress: number, sessionId?: string) => void;
}

interface UseSSEReturn {
  isStreaming: boolean;
  content: string;
  sources: SourceReference[];
  error: string | null;
  startStream: (url: string, body: any) => Promise<void>;
  stopStream: () => void;
}

export const useSSE = (options: UseSSEOptions = {}): UseSSEReturn => {
  const [isStreaming, setIsStreaming] = useState(false);
  const [content, setContent] = useState('');
  const [sources, setSources] = useState<SourceReference[]>([]);
  const [error, setError] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const stopStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const startStream = useCallback(async (url: string, body: any) => {
    // Reset state
    setContent('');
    setSources([]);
    setError(null);
    setIsStreaming(true);

    // Stop any existing stream
    stopStream();

    try {
      // Create abort controller for fetch
      abortControllerRef.current = new AbortController();

      // Make POST request with fetch to get SSE stream
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      // Read stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        // Decode chunk
        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || ''; // Keep incomplete message in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6); // Remove 'data: ' prefix

            try {
              const event: SSEEvent = JSON.parse(data);

              switch (event.type) {
                case 'token':
                  if (event.content) {
                    setContent(prev => prev + event.content);
                    options.onToken?.(event.content);
                  }
                  break;

                case 'sources':
                  if (event.sources) {
                    setSources(event.sources);
                    options.onSources?.(event.sources);
                  }
                  break;

                case 'progress':
                  if (event.progress !== undefined) {
                    options.onProgress?.(event.progress, event.session_id);
                  }
                  break;

                case 'done':
                  if (event.content) {
                    console.log(event)
                    // Sources are optional (e.g., for quiz mode)
                    options.onDone?.(event.content, event.sources || [], event.session_id);
                  }
                  setIsStreaming(false);
                  break;

                case 'error':
                  if (event.content) {
                    setError(event.content);
                    options.onError?.(event.content);
                  }
                  setIsStreaming(false);
                  break;
              }
            } catch (parseError) {
              console.error('Failed to parse SSE event:', parseError);
            }
          }
        }
      }

    } catch (err: any) {
      if (err.name !== 'AbortError') {
        const errorMessage = err.message || 'Unknown error occurred';
        setError(errorMessage);
        options.onError?.(errorMessage);
      }
      setIsStreaming(false);
    }
  }, [options, stopStream]);

  return {
    isStreaming,
    content,
    sources,
    error,
    startStream,
    stopStream
  };
};

