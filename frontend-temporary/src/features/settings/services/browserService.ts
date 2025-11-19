import { apiClient } from '../../../shared/services/api';
import { ApiError } from '../../../shared/types';
import {
  BrowserType,
  BrowserConfigOptions,
  SecretValue,
  BrowserConfigData,
  BulkUpdateBrowserConfigRequest,
  BulkUpdateBrowserConfigResponse,
  BulkUpdateSecretValueRequest,
  BulkUpdateSecretValueResponse
} from '../types';

export class BrowserService {
  private static readonly ENDPOINTS = {
    BROWSER_TYPES: '/browser-types',
    SECRET_VALUES: '/secret-values/project',
    SECRET_VALUES_BULK: '/secret-values/bulk',
    BROWSER_CONFIGS: '/browser-configs/project',
    BROWSER_CONFIGS_BULK: '/browser-configs/bulk',
  };

  /**
   * Fetch all browser configuration options from backend constants
   */
  static async getBrowserConfigOptions(): Promise<BrowserConfigOptions> {
    try {
      const response = await apiClient.get<BrowserConfigOptions>(this.ENDPOINTS.BROWSER_TYPES);
      return response.data;
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to fetch browser configuration options',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Fetch available browser types (for backward compatibility)
   * @deprecated Use getBrowserConfigOptions() instead
   */
  static async getBrowserTypes(): Promise<BrowserType[]> {
    try {
      const options = await this.getBrowserConfigOptions();
      
      // Transform browser channels to options format for backward compatibility
      return options.browser_channels.map(channel => ({
        value: channel,
        label: channel
      }));
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to fetch browser types',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Fetch secret values for a project
   */
  static async getSecretsByProject(
    projectId: string,
    params?: {
      page?: number;
      page_size?: number;
    }
  ): Promise<SecretValue[]> {
    try {
      const queryParams = new URLSearchParams();
      
      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.page_size) queryParams.append('page_size', params.page_size.toString());

      const url = `${this.ENDPOINTS.SECRET_VALUES}/${projectId}${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
      
      const response = await apiClient.get<SecretValue[]>(url);
      return response.data;
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to fetch secrets',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Fetch browser configurations for a project
   */
  static async getBrowserConfigsByProject(
    projectId: string,
    params?: {
      page?: number;
      page_size?: number;
    }
  ): Promise<BrowserConfigData[]> {
    try {
      const queryParams = new URLSearchParams();
      
      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.page_size) queryParams.append('page_size', params.page_size.toString());

      const url = `${this.ENDPOINTS.BROWSER_CONFIGS}/${projectId}${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
      
      const response = await apiClient.get<BrowserConfigData[]>(url);
      return response.data;
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to fetch browser configurations',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Bulk update browser configurations
   */
  static async bulkUpdateBrowserConfigs(requestData: BulkUpdateBrowserConfigRequest): Promise<BulkUpdateBrowserConfigResponse> {
    try {
      const response = await apiClient.put<BulkUpdateBrowserConfigResponse>(
        this.ENDPOINTS.BROWSER_CONFIGS_BULK, 
        requestData
      );
      return response.data;
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to update browser configurations',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Bulk update secret values
   */
  static async bulkUpdateSecretValues(requestData: BulkUpdateSecretValueRequest): Promise<BulkUpdateSecretValueResponse> {
    try {
      const response = await apiClient.put<BulkUpdateSecretValueResponse>(
        this.ENDPOINTS.SECRET_VALUES_BULK, 
        requestData
      );
      return response.data;
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to update secret values',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }
}

export default BrowserService;