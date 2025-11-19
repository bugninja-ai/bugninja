// Global API interfaces
export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export interface ApiError {
  message: string;
  status?: number;
  code?: string;
}

// API Response interfaces for pagination
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Project interfaces matching backend schema
export interface Project {
  id: string;
  name: string;
  default_start_url: string;
  created_at: string; // ISO date string from backend
  updated_at: string; // ISO date string from backend
}

export type ProjectsResponse = PaginatedResponse<Project>;

// Common filter interface
export interface TestFilters {
  search?: string;
  dateFrom?: Date;
  dateTo?: Date;
}