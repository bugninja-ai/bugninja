import { useState, useCallback } from 'react';

export interface AsyncOperationState {
  loading: boolean;
  error: string | null;
  success: boolean;
}

export interface UseAsyncOperationResult {
  loading: boolean;
  error: string | null;
  success: boolean;
  execute: <T>(operation: () => Promise<T>) => Promise<T>;
  reset: () => void;
  setError: (error: string | null) => void;
  setSuccess: (success: boolean) => void;
}

/**
 * Custom hook for managing async operations with loading, error, and success states
 */
export const useAsyncOperation = (initialState?: Partial<AsyncOperationState>): UseAsyncOperationResult => {
  const [state, setState] = useState<AsyncOperationState>({
    loading: false,
    error: null,
    success: false,
    ...initialState,
  });

  const execute = useCallback(async <T>(operation: () => Promise<T>): Promise<T> => {
    setState(prev => ({
      ...prev,
      loading: true,
      error: null,
      success: false,
    }));

    try {
      const result = await operation();
      setState(prev => ({
        ...prev,
        loading: false,
        success: true,
      }));
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
      setState(prev => ({
        ...prev,
        loading: false,
        error: errorMessage,
        success: false,
      }));
      throw error;
    }
  }, []);

  const reset = useCallback(() => {
    setState({
      loading: false,
      error: null,
      success: false,
    });
  }, []);

  const setError = useCallback((error: string | null) => {
    setState(prev => ({
      ...prev,
      error,
      loading: false,
    }));
  }, []);

  const setSuccess = useCallback((success: boolean) => {
    setState(prev => ({
      ...prev,
      success,
    }));
  }, []);

  return {
    loading: state.loading,
    error: state.error,
    success: state.success,
    execute,
    reset,
    setError,
    setSuccess,
  };
};
