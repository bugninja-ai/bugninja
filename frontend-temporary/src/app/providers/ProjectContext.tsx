import React, { createContext, useContext, useEffect, useState } from 'react';
import { Project, ApiState, ApiError } from '../../shared/types';
import { ProjectService } from '../../features/projects/services/projectService';

interface ProjectContextValue {
  projects: Project[] | null;
  selectedProject: Project | null;
  loading: boolean;
  error: string | null;
  setSelectedProject: (project: Project | null) => void;
  refetch: () => Promise<void>;
  createProject: (projectData: { name: string; default_start_url: string }) => Promise<Project>;
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
  const [state, setState] = useState<ApiState<Project[]>>({
    data: null,
    loading: true,
    error: null,
  });
  
  const [selectedProject, setSelectedProjectState] = useState<Project | null>(null);

  const fetchProjects = async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      
      const response = await ProjectService.getProjects({ page: 1, size: 100 });
      
      setState(prev => ({ 
        ...prev, 
        data: response.items, 
        loading: false, 
        error: null 
      }));
      
    } catch (error) {
      const apiError = error as ApiError;
      setState(prev => ({ 
        ...prev, 
        loading: false, 
        error: apiError.message 
      }));
      console.error('Failed to fetch projects:', apiError);
    }
  };

  const refetch = async () => {
    await fetchProjects();
  };

  const createProject = async (projectData: { name: string; default_start_url: string }): Promise<Project> => {
    try {
      const newProject = await ProjectService.createProject(projectData);
      
      // Refetch projects to get the updated list
      await fetchProjects();
      
      // Auto-select the newly created project
      setSelectedProject(newProject);
      
      return newProject;
    } catch (error) {
      const apiError = error as ApiError;
      console.error('Failed to create project:', apiError);
      throw apiError;
    }
  };

  const setSelectedProject = (project: Project | null) => {
    console.log('ProjectContext: Setting selected project to:', project?.name, project?.id);
    setSelectedProjectState(project);
  };

  // Initial fetch on mount
  useEffect(() => {
    fetchProjects();
  }, []);

  // Save selected project to localStorage for persistence
  useEffect(() => {
    if (selectedProject) {
      localStorage.setItem('selectedProjectId', selectedProject.id);
    }
  }, [selectedProject]);

  // Restore selected project from localStorage on mount
  useEffect(() => {
    if (!state.data || state.data.length === 0) return;
    
    const savedProjectId = localStorage.getItem('selectedProjectId');
    
    if (savedProjectId) {
      const savedProject = state.data.find(p => p.id === savedProjectId);
      if (savedProject) {
        setSelectedProject(savedProject);
        return;
      } else {
        // Clear invalid project ID from localStorage
        localStorage.removeItem('selectedProjectId');
      }
    }
    
    // If no saved project or invalid saved project, select first available
    if (!selectedProject && state.data.length > 0) {
      setSelectedProject(state.data[0]);
    }
  }, [state.data, selectedProject]);

  const value: ProjectContextValue = {
    projects: state.data,
    selectedProject,
    loading: state.loading,
    error: state.error,
    setSelectedProject,
    refetch,
    createProject,
  };

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  );
};
