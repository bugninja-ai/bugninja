import { useProjectContext } from '../../app/providers/ProjectContext';

export interface UseProjectsResult {
  data: any[] | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  selectedProject: any | null;
  setSelectedProject: (project: any | null) => void;
  createProject: (projectData: { name: string; default_start_url: string }) => Promise<any>;
}

/**
 * @deprecated Use useProjectContext directly instead
 * This hook is kept for backward compatibility
 */
export const useProjects = (): UseProjectsResult => {
  const {
    projects,
    selectedProject,
    loading,
    error,
    setSelectedProject,
    refetch,
    createProject,
  } = useProjectContext();

  return {
    data: projects,
    loading,
    error,
    refetch,
    selectedProject,
    setSelectedProject,
    createProject,
  };
};