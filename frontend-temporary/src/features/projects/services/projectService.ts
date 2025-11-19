import { apiClient } from '../../../shared/services/api';
import { Project, ProjectsResponse, ApiError } from '../../../shared/types';

export class ProjectService {
  private static readonly ENDPOINTS = {
    PROJECTS: '/projects/',
  };

  /**
   * Fetch all projects with pagination support
   */
  static async getProjects(params?: {
    page?: number;
    size?: number;
    search?: string;
  }): Promise<ProjectsResponse> {
    try {
      const queryParams = new URLSearchParams();
      
      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.size) queryParams.append('size', params.size.toString());
      if (params?.search) queryParams.append('search', params.search);

      const url = `${this.ENDPOINTS.PROJECTS}${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
      
      const response = await apiClient.get<ProjectsResponse>(url);
      return response.data;
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to fetch projects',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Fetch a single project by ID
   */
  static async getProject(id: string): Promise<Project> {
    try {
      const response = await apiClient.get<Project>(`${this.ENDPOINTS.PROJECTS}${id}`);
      return response.data;
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to fetch project',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Create a new project
   */
  static async createProject(project: Omit<Project, 'id' | 'created_at' | 'updated_at'>): Promise<Project> {
    try {
      const response = await apiClient.post<Project>(this.ENDPOINTS.PROJECTS, project);
      return response.data;
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to create project',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Update an existing project
   */
  static async updateProject(id: string, project: Partial<Omit<Project, 'id' | 'created_at' | 'updated_at'>>): Promise<Project> {
    try {
      const response = await apiClient.put<Project>(`${this.ENDPOINTS.PROJECTS}${id}`, project);
      return response.data;
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to update project',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }

  /**
   * Delete a project
   */
  static async deleteProject(id: string): Promise<void> {
    try {
      await apiClient.delete(`${this.ENDPOINTS.PROJECTS}${id}`);
    } catch (error: any) {
      const apiError: ApiError = {
        message: error.response?.data?.detail || error.message || 'Failed to delete project',
        status: error.response?.status,
        code: error.code,
      };
      throw apiError;
    }
  }
}

export default ProjectService; 