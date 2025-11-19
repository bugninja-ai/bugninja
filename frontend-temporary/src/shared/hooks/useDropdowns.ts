import { useState, useCallback } from 'react';

export interface DropdownState {
  [key: string]: boolean;
}

export interface UseDropdownsResult {
  dropdowns: DropdownState;
  isOpen: (key: string) => boolean;
  toggle: (key: string) => void;
  open: (key: string) => void;
  close: (key: string) => void;
  closeAll: () => void;
}

/**
 * Custom hook for managing multiple dropdown states
 * Provides a centralized way to handle dropdown open/close logic
 */
export const useDropdowns = (initialState: DropdownState = {}): UseDropdownsResult => {
  const [dropdowns, setDropdowns] = useState<DropdownState>(initialState);

  const isOpen = useCallback((key: string): boolean => {
    return Boolean(dropdowns[key]);
  }, [dropdowns]);

  const toggle = useCallback((key: string) => {
    setDropdowns(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  }, []);

  const open = useCallback((key: string) => {
    setDropdowns(prev => ({
      ...prev,
      [key]: true
    }));
  }, []);

  const close = useCallback((key: string) => {
    setDropdowns(prev => ({
      ...prev,
      [key]: false
    }));
  }, []);

  const closeAll = useCallback(() => {
    setDropdowns({});
  }, []);

  return {
    dropdowns,
    isOpen,
    toggle,
    open,
    close,
    closeAll,
  };
};
