/**
 * useVideoTimestamp - Hook for handling video player timestamp navigation
 */
import { useCallback } from 'react';

interface VideoPlayerRef {
  seekToTime?: (seconds: number) => void;
}

export const useVideoTimestamp = () => {
  const seekToTime = useCallback((videoRef: React.RefObject<any>, seconds: number) => {
    if (videoRef.current && videoRef.current.seekToTime) {
      videoRef.current.seekToTime(seconds);
    }
  }, []);

  const handleCitationClick = useCallback((
    startTime: number,
    videoUrl: string,
    openInNewTab: boolean = true
  ) => {
    if (openInNewTab) {
      // Open YouTube with timestamp
      const url = `${videoUrl}&t=${startTime}s`;
      window.open(url, '_blank', 'noopener,noreferrer');
    } else {
      // Seek in embedded player
      return startTime;
    }
  }, []);

  return {
    seekToTime,
    handleCitationClick,
  };
};
