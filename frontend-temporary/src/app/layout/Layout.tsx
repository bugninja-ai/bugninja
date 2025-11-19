import React, { useState, useEffect } from 'react';

import { 
  Menu, 
  ChevronDown,
  Loader2,
  AlertCircle,
  RefreshCw,
  FolderPlus
} from 'lucide-react';
import { useProjectContext } from '../providers/ProjectContext';
import { ProjectCreationModal } from '../../features/projects/components/ProjectCreationModal';
import { NavigationSidebar, StarRequestModal } from '../../shared/components';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarMinimized, setSidebarMinimized] = useState(false);
  const [projectDropdownOpen, setProjectDropdownOpen] = useState(false);
  const [createProjectModalOpen, setCreateProjectModalOpen] = useState(false);
  const [createProjectLoading, setCreateProjectLoading] = useState(false);
  const [showStarModal, setShowStarModal] = useState(false);


  // Use project context for global project state
  const { 
    projects, 
    loading: projectsLoading, 
    error: projectsError,
    selectedProject,
    setSelectedProject,
    refetch: refetchProjects,
    createProject
  } = useProjectContext();

  // Handle project creation
  const handleCreateProject = async (projectData: { name: string; default_start_url: string }) => {
    try {
      setCreateProjectLoading(true);
      await createProject(projectData);
      setCreateProjectModalOpen(false);
    } catch (error) {
      console.error('Failed to create project:', error);
      // Error handling is done in the modal component
      throw error;
    } finally {
      setCreateProjectLoading(false);
    }
  };

  // Handle star modal logic
  useEffect(() => {
    // Check if user has already dismissed the star modal
    const starModalDismissed = localStorage.getItem('star-modal-dismissed');
    
    if (!starModalDismissed) {
      // Show the modal after 10 seconds
      const timer = setTimeout(() => {
        setShowStarModal(true);
      }, 10000); // 10 seconds

      return () => clearTimeout(timer);
    }
  }, []);

  const handleStarModalDontShowAgain = () => {
    localStorage.setItem('star-modal-dismissed', 'true');
    setShowStarModal(false);
  };




  const contentMargin = sidebarMinimized ? 'lg:ml-20' : 'lg:ml-72';

  const currentProject = selectedProject;

  const ProjectDropdown = () => {
    return (
      <div className="relative">
        <button
          type="button"
          onClick={() => setProjectDropdownOpen(!projectDropdownOpen)}
          disabled={projectsLoading}
          className="w-full bg-white border border-dashed border-gray-300 rounded-lg px-4 py-3 text-left flex items-center justify-between hover:border-gray-400 transition-colors focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span className="font-medium text-gray-600 truncate flex items-center">
            {projectsLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                Loading projects...
              </>
            ) : currentProject?.name || 'Select Project'}
          </span>
          <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform flex-shrink-0 ${projectDropdownOpen ? 'rotate-180' : ''}`} />
        </button>
        
        {projectDropdownOpen && (
          <>
            {/* Backdrop to close dropdown when clicking outside */}
            <div 
              className="fixed inset-0 z-[9998]" 
              onClick={() => setProjectDropdownOpen(false)}
            />
            {/* Dropdown menu positioned absolutely within the sidebar */}
            <div 
              className="absolute top-full left-0 right-0 mt-1 bg-white border border-dashed border-gray-300 rounded-lg overflow-hidden shadow-xl z-[9999] max-h-60 overflow-y-auto"
            >
              {projectsLoading ? (
                <div className="px-4 py-3 flex items-center justify-center text-gray-500">
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Loading projects...
                </div>
              ) : projectsError ? (
                <div className="px-4 py-3">
                  <div className="flex items-center text-red-600 mb-2">
                    <AlertCircle className="w-4 h-4 mr-2" />
                    Failed to load projects
                  </div>
                  <button
                    onClick={() => {
                      refetchProjects();
                    }}
                    className="flex items-center text-sm text-indigo-600 hover:text-indigo-700"
                  >
                    <RefreshCw className="w-3 h-3 mr-1" />
                    Retry
                  </button>
                </div>
              ) : projects && projects.length > 0 ? (
                <>
                  {/* Existing Projects */}
                  {projects.map((project) => (
                    <button
                      key={project.id}
                      type="button"
                      onClick={() => {
                        console.log('Layout: Selecting project:', project.name, project.id);
                        setSelectedProject(project);
                        setProjectDropdownOpen(false);
                      }}
                      className={`w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors ${
                        project.id === selectedProject?.id ? 'bg-indigo-50' : ''
                      }`}
                    >
                      <span className="font-medium text-gray-600 truncate">{project.name}</span>
                    </button>
                  ))}
                  
                  {/* Separator */}
                  <div className="px-4 py-3">
                    <div className="border-t border-gray-200"></div>
                  </div>
                  
                  {/* Create New Project Button - Primary style at bottom */}
                  <div className="px-4 pb-4">
                    <button
                      type="button"
                      onClick={() => {
                        setCreateProjectModalOpen(true);
                        setProjectDropdownOpen(false);
                      }}
                      className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 px-4 rounded-lg transition-colors flex items-center justify-center space-x-2"
                    >
                      <FolderPlus className="w-4 h-4" />
                      <span>Create New Project</span>
                    </button>
                  </div>
                </>
              ) : (
                <>
                  {/* No projects message */}
                  <div className="px-4 py-3 text-gray-500 text-center text-sm">
                    No projects found
                  </div>
                  
                  {/* Create First Project Button - Primary style */}
                  <div className="px-4 pb-4">
                    <button
                      type="button"
                      onClick={() => {
                        setCreateProjectModalOpen(true);
                        setProjectDropdownOpen(false);
                      }}
                      className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 px-4 rounded-lg transition-colors flex items-center justify-center space-x-2"
                    >
                      <FolderPlus className="w-4 h-4" />
                      <span>Create Your First Project</span>
                    </button>
                  </div>
                </>
              )}
            </div>
          </>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 relative">
      {/* Mobile menu button */}
      <div className="lg:hidden fixed top-4 left-4 z-50">
        <button
          onClick={() => setSidebarOpen(true)}
          className="bg-white/90 backdrop-blur-sm p-2 rounded-lg border border-gray-200"
        >
          <Menu className="w-6 h-6 text-gray-700" />
        </button>
      </div>

      {/* Sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="modal-backdrop fixed bg-black/20 backdrop-blur-sm z-40 lg:hidden"
          style={{ 
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            width: '100vw',
            height: '100vh',
            margin: 0,
            padding: 0
          }}
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <NavigationSidebar
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        sidebarMinimized={sidebarMinimized}
        setSidebarMinimized={setSidebarMinimized}
        currentProject={currentProject}
        projectDropdownComponent={<ProjectDropdown />}
      />

      {/* Main content */}
      <div className={`${contentMargin} min-h-screen transition-all duration-300`}>
        <main className="p-6 lg:p-8">
          {children}
        </main>
      </div>
      
      {/* Project Creation Modal */}
      <ProjectCreationModal
        isOpen={createProjectModalOpen}
        onClose={() => setCreateProjectModalOpen(false)}
        onCreateProject={handleCreateProject}
        loading={createProjectLoading}
      />

      {/* Star Request Modal */}
      <StarRequestModal
        isOpen={showStarModal}
        onClose={() => setShowStarModal(false)}
        onDontShowAgain={handleStarModalDontShowAgain}
      />
    </div>
  );
};

export default Layout; 