// Settings-specific types for browser configs, secrets, etc.
export interface BrowserType {
  value: string;
  label: string;
}

export interface BrowserConfigOptions {
  browser_channels: string[];
  user_agents: string[];
  viewport_sizes: Array<{ width: number; height: number }>;
}

export interface SecretValue {
  id: string;
  project_id: string;
  created_at: string;
  updated_at: string;
  secret_name: string;
  secret_value: string;
}

export interface BrowserConfigData {
  id: string;
  project_id: string;
  created_at: string;
  updated_at: string;
  browser_config: {
    browser_channel?: string;
    user_agent?: string;
    viewport?: {
      width: number;
      height: number;
    };
    device_scale_factor?: number;
    color_scheme?: string;
    accept_downloads?: boolean;
    proxy?: boolean;
    client_certificates?: any[];
    extra_http_headers?: Record<string, string>;
    http_credentials?: any;
    java_script_enabled?: boolean;
    geolocation?: any;
    timeout?: number;
    headers?: Record<string, string>;
    allowed_domains?: string[];
  };
}

export interface UpdateBrowserConfigWithId {
  id: string;
  browser_config: {
    browser_channel?: string;
    user_agent?: string;
    viewport?: {
      width: number;
      height: number;
    };
    geolocation?: {
      latitude: number;
      longitude: number;
    };
  };
}

export interface CreateBrowserConfigRequest {
  test_case_id: string;
  browser_config: {
    browser_channel?: string;
    user_agent?: string;
    viewport?: {
      width: number;
      height: number;
    };
    geolocation?: {
      latitude: number;
      longitude: number;
    };
  };
}

export interface BulkUpdateBrowserConfigRequest {
  browser_configs: UpdateBrowserConfigWithId[];
  new_browser_configs: CreateBrowserConfigRequest[];
  existing_browser_config_ids_to_add: string[];
  browser_config_ids_to_unlink: string[];
  test_case_id?: string;
}

export interface BulkUpdateBrowserConfigResponse {
  updated_browser_configs: BrowserConfigData[];
  created_browser_configs: BrowserConfigData[];
  linked_browser_configs: BrowserConfigData[];
  total_updated: number;
  total_created: number;
  total_linked: number;
  total_unlinked: number;
  failed_updates: any[];
  failed_creations: any[];
  failed_links: any[];
}

// Secret Value interfaces for bulk operations
export interface UpdateSecretValueWithId {
  id: string;
  secret_name?: string;
  secret_value?: string;
}

export interface CreateSecretValueRequest {
  test_case_id: string;
  secret_name: string;
  secret_value: string;
}

export interface BulkUpdateSecretValueRequest {
  secret_values?: UpdateSecretValueWithId[];
  new_secret_values?: CreateSecretValueRequest[];
  existing_secret_value_ids_to_add?: string[];
  secret_value_ids_to_unlink?: string[];
  test_case_id?: string;
}

export interface BulkUpdateSecretValueResponse {
  updated_secret_values: SecretValue[];
  created_secret_values: SecretValue[];
  linked_secret_values: SecretValue[];
  total_updated: number;
  total_created: number;
  total_linked: number;
  total_unlinked: number;
  failed_updates: any[];
  failed_creations: any[];
  failed_links: any[];
}
