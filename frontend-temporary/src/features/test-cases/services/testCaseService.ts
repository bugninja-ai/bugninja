import { apiClient } from '../../../shared/services/api';
import { 
  BackendTestCase, 
  PaginatedTestCasesResponse, 
  FrontendTestCase, 
  TestPriority,
  TestCategory,
  TestStatus,
  ExtraRule,
  BrowserConfig,
  TestSecret
} from '../types';
import { ApiError } from '../../../shared/types';

export class TestCaseService {
  private static readonly ENDPOINTS = {
    TEST_CASES: '/test-cases/',
    TEST_RUNS: '/test-cases/{testCaseId}/test-runs',
    ALL_TEST_RUNS: '/test-runs/',
  };

  /**
   * Transform backend test case to frontend format
   */
  private static transformTestCase(backendTestCase: BackendTestCase): FrontendTestCase {
    // Generate a simple code from the test name (could be improved)
    const code = `TC-${backendTestCase.test_name.slice(0, 3).toUpperCase()}-${backendTestCase.id.slice(-4)}`;
    
    // Map backend priority to frontend priority
    const priorityMap: Record<string, TestPriority> = {
      'low': 'low',
      'medium': 'medium', 
      'high': 'high',
      'critical': 'critical'
    };

    // Map category or use 'general' as fallback
    const categoryMap: Record<string, TestCategory> = {
      'authentication': 'authentication',
      'banking': 'banking',
      'payments': 'payments',
      'security': 'security',
      'ui': 'ui',
      'api': 'api'
    };

    // Transform extra_rules array into ExtraRule array
    
    let extraRules: ExtraRule[] = [];
    
    if (backendTestCase.extra_rules) {
      if (Array.isArray(backendTestCase.extra_rules)) {
        // Check if array contains strings or objects
        const firstItem = backendTestCase.extra_rules[0];
        if (typeof firstItem === 'string') {
          // Handle array of strings
          extraRules = backendTestCase.extra_rules.map((rule, index) => ({
            id: `rule-${backendTestCase.id}-${index + 1}`,
            ruleNumber: index + 1,
            description: rule
          }));
        }
      }
    }

    // Transform backend browser configs to frontend format
    // Note: All data except 'name' comes directly from backend
    // Handle both GET response (has browser_configs) and CREATE response (doesn't have it)
    const browserConfigs: BrowserConfig[] = (backendTestCase.browser_configs || []).map((backendConfig) => ({
      id: backendConfig.id, // ✅ Real backend data
      browserChannel: backendConfig.browser_config.browser_channel || '', // ✅ Real backend data
      userAgent: backendConfig.browser_config.user_agent, // ✅ Real backend data
      viewport: {
        width: backendConfig.browser_config.viewport.width, // ✅ Real backend data
        height: backendConfig.browser_config.viewport.height, // ✅ Real backend data
      },
      geolocation: backendConfig.browser_config.geolocation ? {
        latitude: backendConfig.browser_config.geolocation.latitude,
        longitude: backendConfig.browser_config.geolocation.longitude
      } : undefined, // ✅ Real backend data (may be null)
    }));

    // Transform backend secrets to frontend format
    // Handle both GET response (has secrets) and CREATE response (doesn't have it)
    const secrets: TestSecret[] = (backendTestCase.secrets || []).map(secret => ({
      id: secret.id,
      secretName: secret.secret_name,
      value: secret.secret_value
    }));

    // Calculate test case status based on test run data
    let status: TestStatus = 'pending';
    
    if (backendTestCase.total_runs === 0 || !backendTestCase.last_run_at) {
      // No runs yet - status is pending
      status = 'pending';
    } else if (backendTestCase.pending_runs > 0) {
      // If there are any pending runs, the test case is currently running - status is pending
      status = 'pending';
    } else if (backendTestCase.success_rate >= 100) {
      // All completed runs passed - status is finished
      status = 'finished';
    } else if (backendTestCase.success_rate === 0) {
      // All completed runs failed - status is failed
      status = 'failed';
    } else {
      // Mixed results - use the most recent run result
      // If we have more passed than failed runs, consider it finished
      status = backendTestCase.passed_runs > backendTestCase.failed_runs ? 'finished' : 'failed';
    }

    return {
      id: backendTestCase.id,
      code,
      projectId: backendTestCase.project_id,
      title: backendTestCase.test_name,
      description: backendTestCase.test_description,
      priority: priorityMap[backendTestCase.priority] || 'medium',
      category: categoryMap[backendTestCase.category || ''] || 'general',
      status,
      goal: backendTestCase.test_goal,
      createdAt: new Date(backendTestCase.created_at),
      updatedAt: new Date(backendTestCase.updated_at),
      lastRunAt: backendTestCase.last_run_at ? new Date(backendTestCase.last_run_at) : undefined,
      passRate: backendTestCase.success_rate,
      totalRuns: backendTestCase.total_runs,
      passedRuns: backendTestCase.passed_runs,
      failedRuns: backendTestCase.failed_runs,
      pendingRuns: backendTestCase.pending_runs,
      startingUrl: backendTestCase.url_routes || backendTestCase.url_route || '',
      allowedDomains: backendTestCase.allowed_domains,
      extraRules,
      browserConfigs,
      secrets,
      document: backendTestCase.document
    };
  }

  /**
   * Fetch test cases with pagination and filtering
   */
  static async getTestCases(params?: {
    page?: number;
    page_size?: number;
    sort_order?: 'asc' | 'desc';
    project_id?: string;
    search?: string;
  }): Promise<{
    items: FrontendTestCase[];
    total_count: number;
    page: number;
    page_size: number;
    total_pages: number;
    has_next: boolean;
    has_previous: boolean;
  }> {
    try {
      const queryParams = new URLSearchParams();
      
      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.page_size) queryParams.append('page_size', params.page_size.toString());
      if (params?.sort_order) queryParams.append('sort_order', params.sort_order);
      if (params?.project_id) queryParams.append('project_id', params.project_id);
      if (params?.search) queryParams.append('search', params.search);

      const url = `${this.ENDPOINTS.TEST_CASES}${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
      
      const response = await apiClient.get<PaginatedTestCasesResponse>(url);
      
      // Transform backend test cases to frontend format
      const transformedItems = response.data.items.map(this.transformTestCase);

      return {
        items: transformedItems,
        total_count: response.data.total_count,
        page: response.data.page,
        page_size: response.data.page_size,
        total_pages: response.data.total_pages,
        has_next: response.data.has_next,
        has_previous: response.data.has_previous
      };
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to fetch test cases',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Fetch a single test case by ID
   */
  static async getTestCase(id: string): Promise<FrontendTestCase> {
    try {
      const response = await apiClient.get<BackendTestCase>(`${this.ENDPOINTS.TEST_CASES}${id}`);
      return this.transformTestCase(response.data);
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to fetch test case',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Create a new test case with full payload support
   */
  static async createTestCase(testCase: {
    project_id: string;
    document_id?: string | null;
    test_name: string;
    test_description: string;
    test_goal: string;
    extra_rules: string[];
    url_route: string;
    allowed_domains: string[];
    priority: TestPriority;
    category?: string;
    new_browser_configs?: Array<{
      test_case_id: string;
      browser_config: any;
    }>;
    existing_browser_config_ids?: string[];
    new_secret_values?: Array<{
      test_case_id: string;
      secret_name: string;
      secret_value: string;
    }>;
    existing_secret_value_ids?: string[];
  }): Promise<{
    testCase: FrontendTestCase;
    createdBrowserConfigIds: string[];
    createdSecretValueIds: string[];
  }> {
    try {
      // Send the payload directly as the backend expects it
      const response = await apiClient.post<any>(this.ENDPOINTS.TEST_CASES, testCase);
      // Handle the CreateTestCaseResponse format that includes test_case field
      const fullResponse = response.data;
      const testCaseData = fullResponse.test_case || fullResponse;
      
      // Extract created browser config and secret value IDs
      const createdBrowserConfigIds = (fullResponse.created_browser_configs || []).map((config: any) => config.id);
      const createdSecretValueIds = (fullResponse.created_secret_values || []).map((secret: any) => secret.id);
      
      return {
        testCase: this.transformTestCase(testCaseData),
        createdBrowserConfigIds,
        createdSecretValueIds,
      };
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to create test case',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Update an existing test case
   */
  static async updateTestCase(id: string, testCase: Partial<{
    test_name: string;
    test_description: string;
    test_goal: string;
    extra_rules: string[];
    url_route: string;
    allowed_domains: string[];
    priority: TestPriority;
    category: string;
  }>): Promise<FrontendTestCase> {
    try {
      const payload: Partial<{
        test_name: string;
        test_description: string;
        test_goal: string;
        extra_rules: string[]; // Backend expects array of strings
        url_route: string;
        allowed_domains: string[];
        priority: TestPriority;
        category: string;
      }> = { ...testCase };

      if (testCase.extra_rules) {
        // Backend expects List[str] (array of strings)
        payload.extra_rules = testCase.extra_rules;
      }

      const response = await apiClient.put<BackendTestCase>(`${this.ENDPOINTS.TEST_CASES}${id}`, payload);
      return this.transformTestCase(response.data);
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to update test case',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Delete a test case
   */
  static async deleteTestCase(id: string): Promise<void> {
    try {
      await apiClient.delete(`${this.ENDPOINTS.TEST_CASES}${id}`);
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to delete test case',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Fetch test runs for a specific test case
   */
  static async getTestRuns(testCaseId: string, params?: {
    page?: number;
    page_size?: number;
    sort_order?: 'asc' | 'desc';
  }): Promise<{
    items: any[];
    total_count: number;
    page: number;
    page_size: number;
    total_pages: number;
    has_next: boolean;
    has_previous: boolean;
  }> {
    try {
      const queryParams = new URLSearchParams();
      
      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.page_size) queryParams.append('page_size', params.page_size.toString());
      if (params?.sort_order) queryParams.append('sort_order', params.sort_order);

      const url = this.ENDPOINTS.TEST_RUNS.replace('{testCaseId}', testCaseId);
      const fullUrl = `${url}${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
      
      const response = await apiClient.get<{
        items: any[];
        total_count: number;
        page: number;
        page_size: number;
        total_pages: number;
        has_next: boolean;
        has_previous: boolean;
      }>(fullUrl);
      
      return response.data;
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to fetch test runs',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Fetch the most recent test runs for a test case (for display on detail page)
   */
  static async getRecentTestRuns(testCaseId: string, limit: number = 3): Promise<any[]> {
    try {
      const response = await this.getTestRuns(testCaseId, {
        page: 1,
        page_size: limit,
        sort_order: 'desc'
      });
      
      return response.items;
    } catch (error: any) {
      // If there's an error fetching test runs, return empty array rather than throwing
      console.warn('Failed to fetch recent test runs:', error.message);
      return [];
    }
  }

  /**
   * Fetch a single test run by ID
   */
  static async getTestRun(testRunId: string): Promise<any> {
    try {
      const response = await apiClient.get<any>(`/test-runs/${testRunId}`);
      return response.data;
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to fetch test run',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Fetch all test runs across all test cases with pagination
   */
  static async getAllTestRuns(params?: {
    page?: number;
    page_size?: number;
    sort_order?: 'asc' | 'desc';
    project_id?: string;
    test_case_id?: string;
    search?: string;
    status?: string;
  }): Promise<{
    items: any[];
    total_count: number;
    page: number;
    page_size: number;
    total_pages: number;
    has_next: boolean;
    has_previous: boolean;
  }> {
    try {
      const queryParams = new URLSearchParams();
      
      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.page_size) queryParams.append('page_size', params.page_size.toString());
      if (params?.sort_order) queryParams.append('sort_order', params.sort_order);
      if (params?.project_id) queryParams.append('project_id', params.project_id);
      if (params?.test_case_id) queryParams.append('test_case_id', params.test_case_id);
      if (params?.search) queryParams.append('search', params.search);
      if (params?.status) queryParams.append('status', params.status);

      const url = `${this.ENDPOINTS.ALL_TEST_RUNS}${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
      
      const response = await apiClient.get<{
        items: any[];
        total_count: number;
        page: number;
        page_size: number;
        total_pages: number;
        has_next: boolean;
        has_previous: boolean;
      }>(url);
      
      return response.data;
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to fetch test runs',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Execute a test configuration
   */
  static async executeTestConfiguration(testCaseId: string, browserConfigId: string): Promise<any> {
    try {
      const url = `/test-runs/execute-configuration/${testCaseId}/${browserConfigId}`;
      const response = await apiClient.post(url);
      return response.data;
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to execute test configuration',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Replay a test configuration using previous successful run data
   */
  static async replayTestConfiguration(testCaseId: string, browserConfigId: string): Promise<any> {
    try {
      const url = `/test-runs/replay/${testCaseId}/${browserConfigId}`;
      const response = await apiClient.post(url);
      return response.data;
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to replay test configuration',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Check if a test case has successful runs for a specific browser configuration
   */
  static async hasSuccessfulRuns(testCaseId: string, browserConfigId: string): Promise<boolean> {
    try {
      // Check recent test runs for this test case to see if any are successful with this browser config
      const recentRuns = await this.getRecentTestRuns(testCaseId, 50);
      return recentRuns.some(run => 
        run.browser_config_id === browserConfigId && 
        run.current_state === 'FINISHED' &&
        run.run_type === 'AGENTIC'
      );
    } catch (error: any) {
      console.error('Error checking successful runs:', error);
      return false;
    }
  }
}

export default TestCaseService; 