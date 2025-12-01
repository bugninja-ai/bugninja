import React, { useState, useEffect } from 'react';
import { Edit, Save, X as XIcon, Loader2 } from 'lucide-react';
import { useProjects } from '../../../shared/hooks/useProjects';

export const ProjectSettingsSection: React.FC = () => {
  const { selectedProject, updateProject: updateProjectContext } = useProjects();
  
  // Project editing state
  const [isEditingProject, setIsEditingProject] = useState(false);
  const [editingProject, setEditingProject] = useState<{
    name: string;
    default_start_url: string;
  }>({ name: '', default_start_url: '' });
  const [projectUpdateLoading, setProjectUpdateLoading] = useState(false);

  // Initialize editing project data when selectedProject changes
  useEffect(() => {
    if (selectedProject) {
      setEditingProject({
        name: selectedProject.name,
        default_start_url: selectedProject.default_start_url,
      });
    }
  }, [selectedProject]);

  const handleEditProject = () => {
    setIsEditingProject(true);
  };

  const handleCancelEditProject = () => {
    setIsEditingProject(false);
    if (selectedProject) {
      setEditingProject({
        name: selectedProject.name,
        default_start_url: selectedProject.default_start_url,
      });
    }
  };

  const handleSaveProject = async () => {
    if (!selectedProject) return;

    setProjectUpdateLoading(true);

    try {
      const updateData: { name?: string; default_start_url?: string } = {};
      
      // Only include fields that have changed
      if (editingProject.name !== selectedProject.name) {
        updateData.name = editingProject.name;
      }
      if (editingProject.default_start_url !== selectedProject.default_start_url) {
        updateData.default_start_url = editingProject.default_start_url;
      }

      // If nothing changed, just exit edit mode
      if (Object.keys(updateData).length === 0) {
        setIsEditingProject(false);
        return;
      }

      await updateProjectContext(updateData);
      setIsEditingProject(false);
    } catch (err) {
      console.error('Error updating project:', err);
    } finally {
      setProjectUpdateLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Project Settings</h2>
          <p className="text-gray-600">Update your project name and default URL</p>
        </div>
        {!isEditingProject && (
          <button
            onClick={handleEditProject}
            className="p-2 text-gray-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
            title="Edit project settings"
          >
            <Edit className="w-5 h-5" />
          </button>
        )}
      </div>
      
      <div className="bg-white p-6 rounded-lg border border-gray-200 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Project Name
          </label>
          <input
            type="text"
            value={isEditingProject ? editingProject.name : selectedProject?.name || ''}
            onChange={(e) => isEditingProject && setEditingProject(prev => ({ ...prev, name: e.target.value }))}
            readOnly={!isEditingProject}
            className={`w-full px-3 py-2 border rounded-lg ${
              isEditingProject 
                ? 'border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500' 
                : 'border-gray-300 bg-gray-50 text-gray-500 cursor-not-allowed'
            }`}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Default Start URL
          </label>
          <input
            type="url"
            value={isEditingProject ? editingProject.default_start_url : selectedProject?.default_start_url || ''}
            onChange={(e) => isEditingProject && setEditingProject(prev => ({ ...prev, default_start_url: e.target.value }))}
            readOnly={!isEditingProject}
            className={`w-full px-3 py-2 border rounded-lg ${
              isEditingProject 
                ? 'border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500' 
                : 'border-gray-300 bg-gray-50 text-gray-500 cursor-not-allowed'
            }`}
          />
        </div>
        
        {isEditingProject ? (
          <div className="flex items-center space-x-3">
            <button
              onClick={handleSaveProject}
              disabled={projectUpdateLoading}
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-lg hover:bg-indigo-700 focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {projectUpdateLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              <Save className="w-4 h-4" />
              <span>{projectUpdateLoading ? 'Saving...' : 'Save Changes'}</span>
            </button>
            <button
              onClick={handleCancelEditProject}
              disabled={projectUpdateLoading}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              <XIcon className="w-4 h-4" />
              <span>Cancel</span>
            </button>
          </div>
        ) : (
          <div className="text-sm text-gray-500">
            Click the edit icon to modify project settings
          </div>
        )}
      </div>

    </div>
  );
};
