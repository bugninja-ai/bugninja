import { apiClient } from '../../../shared/services/api';

export interface ParsedTestCaseData {
  test_name: string;
  test_description: string;
  test_goal: string;
  extra_rules: string[];
  url_route: string;
  allowed_domains: string[];
  priority: 'low' | 'medium' | 'high' | 'critical';
  category?: string;
  viewport?: { width: number; height: number };
}

export interface ParsedBrowserConfig {
  channel: string;
  user_agent: string;
  viewport: { width: number; height: number };
  device_scale_factor: number;
  color_scheme: string;
  accept_downloads: boolean;
  proxy?: string;
  client_certificates: string[];
  extra_http_headers: Record<string, string>;
  http_credentials?: string;
  java_script_enabled: boolean;
  geolocation?: { latitude: number; longitude: number };
  timeout: number;
  headers?: Record<string, string>;
  allowed_domains: string[];
}

export interface FileUploadResponse {
  success: boolean;
  message: string;
  parsed_data?: ParsedTestCaseData;
  browser_config?: ParsedBrowserConfig;
  error?: string;
}

export class FileUploadService {
  /**
   * Parse an uploaded file into test case format using OpenAI
   */
  static async parseTestCaseFile(file: File, projectId: string): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', projectId);

    const response = await apiClient.post<FileUploadResponse>('/file-upload/parse-test-case', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }
}
