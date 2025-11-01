import React from 'react';
import { useTranslation } from 'react-i18next';
import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { Button } from './ui/button';

export const ThemeSwitcher = ({ variant = 'default', showLabel = true }) => {
  const { theme, toggleTheme } = useTheme();
  const { t } = useTranslation();

  if (variant === 'icon-only') {
    return (
      <Button
        variant="ghost"
        size="icon"
        onClick={toggleTheme}
        title={theme === 'light' ? t('theme.dark') : t('theme.light')}
      >
        {theme === 'light' ? (
          <Moon className="h-5 w-5" />
        ) : (
          <Sun className="h-5 w-5" />
        )}
      </Button>
    );
  }

  return (
    <Button
      variant="outline"
      onClick={toggleTheme}
      className="flex items-center gap-2"
    >
      {theme === 'light' ? (
        <Moon className="h-4 w-4" />
      ) : (
        <Sun className="h-4 w-4" />
      )}
      {showLabel && (
        <span className="text-sm">
          {theme === 'light' ? t('theme.dark') : t('theme.light')}
        </span>
      )}
    </Button>
  );
};
