import { apiClient } from '../../../shared/services/api';

export interface BrowserConfig {
  id: string;
  project_id: string;
  created_at: string;
  updated_at: string;
  browser_config: {
    browser_channel?: string;
    user_agent?: string;
    viewport?: { width: number; height: number };
    device_scale_factor?: number | null;
    color_scheme?: 'light' | 'dark';
    accept_downloads?: boolean;
    proxy?: boolean;
    client_certificates?: any[];
    extra_http_headers?: Record<string, any>;
    http_credentials?: any;
    java_script_enabled?: boolean;
    geolocation?: string;
    timeout?: number;
    headers?: Record<string, string>;
    allowed_domains?: string[];
  } | null;
}

export interface SecretValue {
  id: string;
  project_id: string;
  created_at: string;
  updated_at: string;
  secret_name: string;
  secret_value: string;
}

export interface Project {
  id: string;
  created_at: string;
  name: string;
  default_start_url: string;
}

export interface UpdateProjectData {
  name?: string;
  default_start_url?: string;
}

export const settingsService = {
  async getBrowserConfigs(projectId: string, pageSize: number = 100): Promise<BrowserConfig[]> {
    // Using a large page size to get all configs, adjust as needed
    const response = await apiClient.get(
      `/browser-configs/project/${projectId}?page=1&page_size=${pageSize}`
    );
    return response.data;
  },

  async getSecretValues(projectId: string, pageSize: number = 100): Promise<SecretValue[]> {
    // Using a large page size to get all secrets, adjust as needed
    const response = await apiClient.get(
      `/secret-values/project/${projectId}?page=1&page_size=${pageSize}`
    );
    return response.data;
  },

  async deleteBrowserConfig(configId: string): Promise<{ success: boolean; error?: string }> {
    try {
      await apiClient.delete(`/browser-configs/${configId}`);
      return { success: true };
    } catch (error: any) {
      if (error.response?.status === 409) {
        return { 
          success: false, 
          error: error.response.data?.detail || 'Cannot delete browser configuration - it is still in use' 
        };
      }
      return { 
        success: false, 
        error: error.response?.data?.detail || error.message || 'Unknown error occurred' 
      };
    }
  },

  async deleteSecretValue(secretId: string): Promise<{ success: boolean; error?: string }> {
    try {
      await apiClient.delete(`/secret-values/${secretId}`);
      return { success: true };
    } catch (error: any) {
      if (error.response?.status === 409) {
        return { 
          success: false, 
          error: error.response.data?.detail || 'Cannot delete secret value - it is still in use' 
        };
      }
      return { 
        success: false, 
        error: error.response?.data?.detail || error.message || 'Unknown error occurred' 
      };
    }
  },

  async updateProject(projectId: string, projectData: UpdateProjectData): Promise<{ success: boolean; error?: string; project?: Project }> {
    try {
      const response = await apiClient.put(`/projects/${projectId}`, projectData);
      return { success: true, project: response.data };
    } catch (error: any) {
      return { 
        success: false, 
        error: error.response?.data?.detail || error.message || 'Unknown error occurred' 
      };
    }
  },
};