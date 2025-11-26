import { useProjectContext } from '../../app/providers/ProjectContext';

/**
 * Compatibility hook for single-project mode
 * 
 * Maps the new single-project context to the old multi-project interface
 * for backward compatibility with existing components.
 */
export interface UseProjectsResult {
  data: any | null;  // Single project instead of array
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  selectedProject: any | null;  // For compatibility - same as project
  updateProject: (projectData: { name?: string; default_start_url?: string }) => Promise<any>;
}

/**
 * Hook for accessing project information (single-project mode)
 * 
 * @deprecated Use useProjectContext directly for clearer semantics
 * This hook is kept for backward compatibility with multi-project code
 */
export const useProjects = (): UseProjectsResult => {
  const {
    project,
    loading,
    error,
    refetch,
    updateProject,
  } = useProjectContext();

  return {
    data: project,
    loading,
    error,
    refetch,
    selectedProject: project,  // Alias for compatibility
    updateProject,
  };
};