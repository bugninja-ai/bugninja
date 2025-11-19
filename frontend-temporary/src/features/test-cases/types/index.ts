export type TestStatus = 'finished' | 'failed' | 'pending' | 'skipped';
export type TestPriority = 'critical' | 'high' | 'medium' | 'low';
export type TestCategory = 'authentication' | 'banking' | 'payments' | 'security' | 'ui' | 'api';

export interface BrowserConfig {
  id: string;
  browserChannel: string;
  userAgent: string;
  viewport: {
    width: number;
    height: number;
  };
  geolocation?: {
    latitude: number;
    longitude: number;
  };
}

export interface TestSecret {
  id: string;
  secretName: string;
  value: string;
}

export interface ExtraRule {
  id: string;
  ruleNumber: number;
  description: string;
}

export interface TestCase {
  id: string;
  code: string; // e.g., "TC-001"
  projectId: string;
  title: string;
  description: string;
  priority: TestPriority;
  category: TestCategory;
  status: TestStatus;
  goal: string;
  createdAt: Date;
  updatedAt: Date;
  lastRunAt?: Date;
  passRate: number; // percentage
  totalRuns: number;
  passedRuns: number;
  failedRuns: number;
  // Additional configuration fields
  startingUrl: string;
  allowedDomains: string[];
  extraRules: ExtraRule[];
  browserConfigs: BrowserConfig[];
  secrets: TestSecret[];
}

export interface CreateTestCaseRequest {
  title: string;
  description: string;
  priority: TestPriority;
  category: TestCategory;
  goal: string;
  steps?: string[];
  file?: File;
}

// Backend Test Case Types (matching API schema)
export interface BackendDocument {
  id: string;
  project_id: string;
  created_at: string;
  updated_at: string;
  name: string;
  content: string;
}

export interface BackendBrowserConfig {
  id: string;
  project_id: string;
  created_at: string;
  updated_at: string;
  browser_config: {
    browser_channel?: string;
    user_agent: string;
    viewport: {
      width: number;
      height: number;
    };
    device_scale_factor: number;
    color_scheme: 'light' | 'dark';
    accept_downloads: boolean;
    client_certificates: any[];
    extra_http_headers: Record<string, string>;
    java_script_enabled: boolean;
    timeout: number;
    allowed_domains: string[];
    geolocation: {
      latitude: number;
      longitude: number;
    } | null;
  };
}

export interface BackendSecretValue {
  id: string;
  project_id: string;
  created_at: string;
  updated_at: string;
  secret_name: string;
  secret_value: string;
}

export interface BackendTestCase {
  id: string;
  project_id: string;
  document: BackendDocument | null;
  browser_configs: BackendBrowserConfig[];
  secrets: BackendSecretValue[];
  created_at: string;
  updated_at: string;
  test_name: string;
  test_description: string;
  test_goal: string;
  extra_rules: string[];
  url_routes: string;
  url_route?: string; // Used by PUT endpoint response
  allowed_domains: string[];
  priority: 'low' | 'medium' | 'high' | 'critical';
  category: string | null;
  total_runs: number;
  passed_runs: number;
  failed_runs: number;
  pending_runs: number;
  success_rate: number;
  last_run_at: string | null;
}

export interface PaginatedTestCasesResponse {
  items: BackendTestCase[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

// Transformed types for frontend usage
export interface FrontendTestCase {
  id: string;
  code: string;
  projectId: string;
  title: string;
  description: string;
  priority: TestPriority;
  category: TestCategory | 'general';
  status: TestStatus;
  goal: string;
  createdAt: Date;
  updatedAt: Date;
  lastRunAt?: Date;
  passRate: number;
  totalRuns: number;
  passedRuns: number;
  failedRuns: number;
  pendingRuns: number;
  startingUrl: string;
  allowedDomains: string[];
  extraRules: ExtraRule[];
  browserConfigs: BrowserConfig[];
  secrets: TestSecret[];
  document: BackendDocument | null;
  existingBrowserConfigIds?: string[]; // For linking existing browser configs
  existingSecretIds?: string[]; // For linking existing secrets
}
