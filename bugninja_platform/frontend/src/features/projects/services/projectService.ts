import { apiClient } from '../../../shared/services/api';
import { Project, ApiError } from '../../../shared/types';

/**
 * ProjectService for single-project mode
 * 
 * This service handles operations for the current Bugninja project.
 * Unlike multi-project mode, there is only one active project at a time
 * (the project initialized with `bugninja init`).
 */
export class ProjectService {
  private static readonly ENDPOINTS = {
    PROJECT: '/project',  // Single project endpoint
  };

  /**
   * Fetch the current project information
   */
  static async getProject(): Promise<Project> {
    try {
      const response = await apiClient.get<Project>(this.ENDPOINTS.PROJECT);
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
   * Update the current project
   */
  static async updateProject(project: Partial<Omit<Project, 'id' | 'created_at' | 'updated_at'>>): Promise<Project> {
    try {
      const response = await apiClient.put<Project>(this.ENDPOINTS.PROJECT, project);
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
}

export default ProjectService; 