import React, { createContext, useContext, useEffect, useState } from 'react';
import { Project, ApiState, ApiError } from '../../shared/types';
import { ProjectService } from '../../features/projects/services/projectService';

/**
 * ProjectContext for single-project mode
 * 
 * In single-project mode, there's only one active project (the current directory's
 * bugninja.toml). We fetch it once on mount and provide update capabilities.
 */
interface ProjectContextValue {
  project: Project | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  updateProject: (projectData: { name?: string; default_start_url?: string }) => Promise<Project>;
}

const ProjectContext = createContext<ProjectContextValue | undefined>(undefined);

export const useProjectContext = () => {
  const context = useContext(ProjectContext);
  if (context === undefined) {
    throw new Error('useProjectContext must be used within a ProjectProvider');
  }
  return context;
};

interface ProjectProviderProps {
  children: React.ReactNode;
}

export const ProjectProvider: React.FC<ProjectProviderProps> = ({ children }) => {
  const [state, setState] = useState<ApiState<Project>>({
    data: null,
    loading: true,
    error: null,
  });
  
  const fetchProject = async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      
      const project = await ProjectService.getProject();
      
      setState({ 
        data: project, 
        loading: false, 
        error: null 
      });
      
    } catch (error) {
      const apiError = error as ApiError;
      setState({ 
        data: null,
        loading: false, 
        error: apiError.message 
      });
      console.error('Failed to fetch project:', apiError);
    }
  };

  const refetch = async () => {
    await fetchProject();
  };

  const updateProject = async (projectData: { name?: string; default_start_url?: string }): Promise<Project> => {
    try {
      const updatedProject = await ProjectService.updateProject(projectData);
      
      // Update local state
      setState(prev => ({ 
        ...prev, 
        data: updatedProject 
      }));
      
      return updatedProject;
    } catch (error) {
      const apiError = error as ApiError;
      console.error('Failed to update project:', apiError);
      throw apiError;
    }
  };

  // Initial fetch on mount
  useEffect(() => {
    fetchProject();
  }, []);

  const value: ProjectContextValue = {
    project: state.data,
    loading: state.loading,
    error: state.error,
    refetch,
    updateProject,
  };

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  );
};
