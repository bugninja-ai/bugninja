import React, { useState, useEffect } from 'react';

import { 
  Menu, 
  Loader2,
  AlertCircle,
  RefreshCw
} from 'lucide-react';
import { useProjectContext } from '../providers/ProjectContext';
import { NavigationSidebar, StarRequestModal } from '../../shared/components';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarMinimized, setSidebarMinimized] = useState(false);
  const [showStarModal, setShowStarModal] = useState(false);

  // Use project context for global project state (single project mode)
  const { 
    project, 
    loading: projectLoading, 
    error: projectError,
    refetch: refetchProject
  } = useProjectContext();

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

  // Single project display component
  const ProjectDisplay = () => {
    return (
      <div className="w-full bg-white border border-dashed border-gray-300 rounded-lg px-4 py-3">
        <div className="font-medium text-gray-600 truncate flex items-center">
          {projectLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
              Loading project...
            </>
          ) : projectError ? (
            <>
              <AlertCircle className="w-4 h-4 mr-2 text-red-500" />
              <span className="text-red-600">Failed to load</span>
              <button
                onClick={refetchProject}
                className="ml-2 text-indigo-600 hover:text-indigo-700"
                title="Retry loading project"
              >
                <RefreshCw className="w-3 h-3" />
              </button>
            </>
          ) : project?.name || 'No Project'}
        </div>
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
        currentProject={project}
        projectDropdownComponent={<ProjectDisplay />}
      />

      {/* Main content */}
      <div className={`${contentMargin} min-h-screen transition-all duration-300`}>
        <main className="p-6 lg:p-8">
          {children}
        </main>
      </div>
      
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