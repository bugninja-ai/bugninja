import { useState, useEffect, useCallback } from 'react';
import { FrontendTestCase, TestPriority, TestCategory } from '../types';
import { ApiState, ApiError } from '../../../shared/types';
import { TestCaseService } from '../services/testCaseService';

export interface UseTestCasesParams {
  projectId?: string;
  page?: number;
  pageSize?: number;
  search?: string;
  priority?: TestPriority;
  category?: TestCategory;
  sortOrder?: 'asc' | 'desc';
}

export interface UseTestCasesResult extends ApiState<FrontendTestCase[]> {
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
  setPriority: (priority: TestPriority | undefined) => void;
  setCategory: (category: TestCategory | undefined) => void;
  setSortOrder: (sortOrder: 'asc' | 'desc') => void;
  
  // Current filters
  filters: {
    search: string;
    priority?: TestPriority;
    category?: TestCategory;
    sortOrder: 'asc' | 'desc';
  };
}

export const useTestCases = (params?: UseTestCasesParams): UseTestCasesResult => {
  const [state, setState] = useState<ApiState<FrontendTestCase[]>>({
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
  const [priority, setPriorityState] = useState<TestPriority | undefined>(params?.priority);
  const [category, setCategoryState] = useState<TestCategory | undefined>(params?.category);
  const [sortOrder, setSortOrderState] = useState<'asc' | 'desc'>(params?.sortOrder || 'desc');

  const fetchTestCases = useCallback(async () => {
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
      
      const response = await TestCaseService.getTestCases({
        page,
        page_size: pageSize,
        sort_order: sortOrder,
        project_id: projectId,
        search: search || undefined,
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
      if (apiError.status === 404 && projectId && apiError.message?.includes('not found')) {
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
      
      setState(prev => ({ 
        ...prev, 
        loading: false, 
        error: apiError.message 
      }));
    }
  }, [page, pageSize, sortOrder, projectId, search]);

  const refetch = useCallback(async () => {
    await fetchTestCases();
  }, [fetchTestCases]);

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

  const setPriority = useCallback((newPriority: TestPriority | undefined) => {
    setPriorityState(newPriority);
    setPageState(1); // Reset to first page when filtering
  }, []);

  const setCategory = useCallback((newCategory: TestCategory | undefined) => {
    setCategoryState(newCategory);
    setPageState(1); // Reset to first page when filtering
  }, []);

  const setSortOrder = useCallback((newSortOrder: 'asc' | 'desc') => {
    setSortOrderState(newSortOrder);
    setPageState(1); // Reset to first page when sorting
  }, []);

  // Fetch data when dependencies change
  useEffect(() => {
    if (projectId) {
      fetchTestCases();
    }
  }, [fetchTestCases, projectId]);

  // Client-side filtering for priority and category (since backend might not support all filters)
  const filteredData = state.data?.filter(testCase => {
    if (priority && testCase.priority !== priority) return false;
    if (category && testCase.category !== category) return false;
    return true;
  }) || null;

  return {
    data: filteredData,
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
    setPriority,
    setCategory,
    setSortOrder,
    filters: {
      search,
      priority,
      category,
      sortOrder,
    },
  };
}; 