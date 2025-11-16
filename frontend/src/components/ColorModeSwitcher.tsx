/**
 * ColorModeSwitcher - Toggle between light and dark mode
 */
import React from 'react';
import { IconButton, useColorMode, useColorModeValue } from '@chakra-ui/react';
import { MoonIcon, SunIcon } from '@chakra-ui/icons';

interface ColorModeSwitcherProps {
  position?: 'fixed' | 'absolute' | 'relative';
}

export const ColorModeSwitcher: React.FC<ColorModeSwitcherProps> = ({ position = 'fixed' }) => {
  const { toggleColorMode } = useColorMode();
  const text = useColorModeValue('dark', 'light');
  const SwitchIcon = useColorModeValue(MoonIcon, SunIcon);

  return (
    <IconButton
      size="md"
      fontSize="lg"
      aria-label={`Switch to ${text} mode`}
      variant="ghost"
      color="current"
      onClick={toggleColorMode}
      icon={<SwitchIcon />}
      position={position}
      top={position === 'fixed' || position === 'absolute' ? 4 : undefined}
      right={position === 'fixed' || position === 'absolute' ? 4 : undefined}
      zIndex={position === 'fixed' || position === 'absolute' ? 10 : undefined}
      _hover={{
        bg: useColorModeValue('gray.200', 'gray.700'),
      }}
    />
  );
};
