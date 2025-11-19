import { useState, useEffect, useCallback } from 'react';
import { ApiState, ApiError } from '../../../shared/types';
import { TestCaseService } from '../../test-cases/services/testCaseService';

export interface UseTestRunsParams {
  page?: number;
  pageSize?: number;
  search?: string;
  status?: string;
  sortOrder?: 'asc' | 'desc';
  projectId?: string;
  testCaseId?: string;
}

export interface UseTestRunsResult extends ApiState<any[]> {
  // Pagination info
  totalCount: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
  
  // Actions
  refetch: () => Promise<void>;
  setPage: (page: number) => void;
  setPageSize: (pageSize: number) => void;
  setSearch: (search: string) => void;
  setStatus: (status: string | undefined) => void;
  setSortOrder: (sortOrder: 'asc' | 'desc') => void;
  setTestCaseId: (id: string | undefined) => void;
  
  // Current filters
  filters: {
    search: string;
    status?: string;
    sortOrder: 'asc' | 'desc';
    testCaseId?: string;
  };
}

export const useTestRuns = (params?: UseTestRunsParams): UseTestRunsResult => {
  const [state, setState] = useState<ApiState<any[]>>({
    data: null,
    loading: true,
    error: null,
  });

  // Make projectId reactive
  const projectId = params?.projectId;

  // Pagination state
  const [page, setPageState] = useState(params?.page || 1);
  const [pageSize, setPageSizeState] = useState(params?.pageSize || 15);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);

  // Filter state
  const [search, setSearchState] = useState(params?.search || '');
  const [status, setStatusState] = useState<string | undefined>(params?.status);
  const [sortOrder, setSortOrderState] = useState<'asc' | 'desc'>(params?.sortOrder || 'desc');
  const [testCaseId, setTestCaseIdState] = useState<string | undefined>(params?.testCaseId);

  const fetchTestRuns = useCallback(async () => {
    if (!projectId) {
      setState(prev => ({ 
        ...prev, 
        data: null, 
        loading: false, 
        error: null 
      }));
      return;
    }

    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      
      const response = await TestCaseService.getAllTestRuns({
        page,
        page_size: pageSize,
        sort_order: sortOrder,
        project_id: projectId,
        test_case_id: testCaseId,
        search: search || undefined,
        status: status || undefined,
      });
      
      setState(prev => ({ 
        ...prev, 
        data: response.items, 
        loading: false, 
        error: null 
      }));

      // Update pagination info
      setTotalCount(response.total_count);
      setTotalPages(response.total_pages);
      setHasNext(response.has_next);
      setHasPrevious(response.has_previous);
      
    } catch (error) {
      const apiError = error as ApiError;
      
      // If project not found, it might be deleted - clear localStorage and reset
      if (apiError.status === 404 && projectId && apiError.message?.includes('Project') && apiError.message?.includes('not found')) {
        localStorage.removeItem('selectedProjectId');
        // Don't show error for invalid project - let useProjects handle it
        setState(prev => ({ 
          ...prev, 
          loading: false, 
          error: null,
          data: []
        }));
        return;
      }
      
      // If we get a 404 for test case not found, clear the filter and retry
      if (apiError.status === 404 && testCaseId && apiError.message?.includes('not found')) {
        setTestCaseIdState(undefined);
        return; // This will trigger a re-fetch with the cleared filter
      }
      
      setState(prev => ({ 
        ...prev, 
        loading: false, 
        error: apiError.message 
      }));
    }
  }, [page, pageSize, sortOrder, projectId, testCaseId, search, status]);

  const refetch = useCallback(async () => {
    await fetchTestRuns();
  }, [fetchTestRuns]);

  // Reset to first page when filters change
  const setPage = useCallback((newPage: number) => {
    setPageState(newPage);
  }, []);

  const setPageSize = useCallback((newPageSize: number) => {
    setPageSizeState(newPageSize);
    setPageState(1); // Reset to first page when changing page size
  }, []);

  const setSearch = useCallback((newSearch: string) => {
    setSearchState(newSearch);
    setPageState(1); // Reset to first page when searching
  }, []);

  const setStatus = useCallback((newStatus: string | undefined) => {
    setStatusState(newStatus);
    setPageState(1); // Reset to first page when filtering
  }, []);

  const setSortOrder = useCallback((newSortOrder: 'asc' | 'desc') => {
    setSortOrderState(newSortOrder);
    setPageState(1); // Reset to first page when sorting
  }, []);

  const setTestCaseId = useCallback((newId: string | undefined) => {
    setTestCaseIdState(newId);
    setPageState(1); // Reset to first page when filtering
  }, []);

  // Fetch data when dependencies change
  useEffect(() => {
    if (projectId) {
      fetchTestRuns();
    }
  }, [fetchTestRuns, projectId]);

  // No client-side filtering needed - all filtering is handled by the backend

  return {
    data: state.data,
    loading: state.loading,
    error: state.error,
    totalCount,
    page,
    pageSize,
    totalPages,
    hasNext,
    hasPrevious,
    refetch,
    setPage,
    setPageSize,
    setSearch,
    setStatus,
    setSortOrder,
    setTestCaseId,
    filters: {
      search,
      status,
      sortOrder,
      testCaseId,
    },
  };
}; 