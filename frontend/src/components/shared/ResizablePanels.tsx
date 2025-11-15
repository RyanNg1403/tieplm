/**
 * ResizablePanels - A component that provides resizable split panels
 * Supports both horizontal (side-by-side) and vertical (stacked) layouts
 */
import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Box, HStack, VStack } from '@chakra-ui/react';

interface ResizablePanelsProps {
  direction?: 'horizontal' | 'vertical';
  defaultSizes?: [number, number]; // Percentage sizes [first, second]
  minSizes?: [number, number]; // Minimum percentage sizes
  children: [React.ReactNode, React.ReactNode];
  className?: string;
}

export const ResizablePanels: React.FC<ResizablePanelsProps> = ({
  direction = 'horizontal',
  defaultSizes = [50, 50],
  minSizes = [20, 20],
  children,
  className,
}) => {
  const [sizes, setSizes] = useState<[number, number]>(defaultSizes);
  const [isResizing, setIsResizing] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const startPosRef = useRef<number>(0);
  const startSizesRef = useRef<[number, number]>([0, 0]);
  const isResizingRef = useRef(false);
  const directionRef = useRef(direction);
  const minSizesRef = useRef(minSizes);

  // Update refs when props change
  useEffect(() => {
    directionRef.current = direction;
    minSizesRef.current = minSizes;
  }, [direction, minSizes]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isResizingRef.current || !containerRef.current) return;

    const container = containerRef.current;
    const containerSize = directionRef.current === 'horizontal' 
      ? container.offsetWidth 
      : container.offsetHeight;
    
    const currentPos = directionRef.current === 'horizontal' ? e.clientX : e.clientY;
    const delta = currentPos - startPosRef.current;
    const deltaPercent = (delta / containerSize) * 100;

    const [firstSize, secondSize] = startSizesRef.current;
    let newFirstSize = firstSize + deltaPercent;
    let newSecondSize = secondSize - deltaPercent;

    // Apply minimum size constraints
    const [minFirst, minSecond] = minSizesRef.current;
    if (newFirstSize < minFirst) {
      newFirstSize = minFirst;
      newSecondSize = 100 - minFirst;
    } else if (newSecondSize < minSecond) {
      newSecondSize = minSecond;
      newFirstSize = 100 - minSecond;
    }

    setSizes([newFirstSize, newSecondSize]);
  }, []);

  const handleMouseUp = useCallback(() => {
    isResizingRef.current = false;
    setIsResizing(false);
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  }, [handleMouseMove]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isResizingRef.current = true;
    setIsResizing(true);
    startPosRef.current = directionRef.current === 'horizontal' ? e.clientX : e.clientY;
    startSizesRef.current = [...sizes] as [number, number];
    
    // Add global mouse event listeners
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [sizes, handleMouseMove, handleMouseUp]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  // Make divider more touch-friendly with larger hit area
  const dividerHitArea = direction === 'horizontal' ? 8 : 8; // 8px on each side = 16px total
  const dividerStyle = {
    [direction === 'horizontal' ? 'width' : 'height']: `${dividerHitArea * 2}px`,
    [direction === 'horizontal' ? 'height' : 'width']: '100%',
    cursor: direction === 'horizontal' ? 'col-resize' : 'row-resize',
    bg: isResizing ? 'blue.400' : 'transparent',
    _hover: {
      bg: 'blue.200',
    },
    transition: isResizing ? 'none' : 'background-color 0.2s',
    position: 'relative' as const,
    zIndex: 10,
    flexShrink: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  } as const;

  // Visual indicator line in the center
  const indicatorStyle = {
    [direction === 'horizontal' ? 'width' : 'height']: '2px',
    [direction === 'horizontal' ? 'height' : 'width']: '60%',
    bg: isResizing ? 'blue.500' : 'gray.400',
    borderRadius: '1px',
    transition: isResizing ? 'none' : 'background-color 0.2s',
  } as const;

  const Container = direction === 'horizontal' ? HStack : VStack;

  return (
    <Container
      ref={containerRef}
      spacing={0}
      align="stretch"
      h="100%"
      w="100%"
      className={className}
    >
      {/* First Panel */}
      <Box
        flex={`0 0 ${sizes[0]}%`}
        minW={direction === 'horizontal' ? `${minSizes[0]}%` : undefined}
        minH={direction === 'vertical' ? `${minSizes[0]}%` : undefined}
        overflow="hidden"
        position="relative"
      >
        {children[0]}
      </Box>

      {/* Resizable Divider */}
      <Box
        {...dividerStyle}
        onMouseDown={handleMouseDown}
        role="separator"
        aria-label="Resize panels"
        aria-orientation={direction}
      >
        <Box {...indicatorStyle} />
      </Box>

      {/* Second Panel */}
      <Box
        flex={`0 0 ${sizes[1]}%`}
        minW={direction === 'horizontal' ? `${minSizes[1]}%` : undefined}
        minH={direction === 'vertical' ? `${minSizes[1]}%` : undefined}
        overflow="hidden"
        position="relative"
      >
        {children[1]}
      </Box>
    </Container>
  );
};

