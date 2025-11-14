/**
 * VideoPlayer - Video player component with timestamp navigation
 * Displays a video with clickable timestamps from citations
 */
import React, { useRef, useEffect } from 'react';
import { Box, VStack, HStack, Text, IconButton } from '@chakra-ui/react';
import { TriangleUpIcon, MinusIcon } from '@chakra-ui/icons';

interface VideoPlayerProps {
  videoUrl: string;
  videoTitle: string;
  onTimeUpdate?: (currentTime: number) => void;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  videoUrl,
  videoTitle,
  onTimeUpdate,
}: VideoPlayerProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (videoRef.current.paused) {
        videoRef.current.play();
      } else {
        videoRef.current.pause();
      }
    }
  };

  const seekToTime = (seconds: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = seconds;
      videoRef.current.play();
    }
  };

  // Expose seek function to parent component via ref
  useEffect(() => {
    if (videoRef.current) {
      (videoRef.current as any).seekToTime = seekToTime;
    }
  }, []);

  const handleTimeUpdate = () => {
    if (videoRef.current && onTimeUpdate) {
      onTimeUpdate(videoRef.current.currentTime);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <VStack w="full" spacing={4} align="stretch">
      <Box
        bg="black"
        borderRadius="md"
        overflow="hidden"
        w="full"
        aspectRatio="16/9"
      >
        <video
          ref={videoRef}
          width="100%"
          height="100%"
          onTimeUpdate={handleTimeUpdate}
          style={{ display: 'block' }}
          crossOrigin="anonymous"
        >
          <source src={videoUrl} type="video/mp4" />
          Your browser does not support the video tag.
        </video>
      </Box>

      <VStack spacing={2} w="full">
        <Text fontSize="lg" fontWeight="bold">
          {videoTitle}
        </Text>

        <HStack w="full" justify="space-between" px={2}>
          <IconButton
            aria-label="Play/Pause"
            icon={videoRef.current?.paused ? <TriangleUpIcon transform="rotate(90deg)" /> : <MinusIcon />}
            onClick={handlePlayPause}
            size="lg"
            colorScheme="blue"
          />

          {videoRef.current && (
            <Text fontSize="sm" color="gray.600">
              {formatTime(videoRef.current.currentTime)} /{' '}
              {formatTime(videoRef.current.duration || 0)}
            </Text>
          )}
        </HStack>

        {videoRef.current && (
          <Box w="full" px={2}>
            <input
              type="range"
              min="0"
              max={videoRef.current.duration || 0}
              value={videoRef.current.currentTime}
              onChange={(e: React.ChangeEvent<HTMLInputElement>): void => {
                const newTime = parseFloat(e.currentTarget.value);
                if (videoRef.current) {
                  videoRef.current.currentTime = newTime;
                }
              }}
              style={{
                width: '100%',
                cursor: 'pointer',
              }}
            />
          </Box>
        )}
      </VStack>
    </VStack>
  );
};
