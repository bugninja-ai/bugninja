import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trash2, X as XIcon, Globe, AlertCircle, Loader2 } from 'lucide-react';
import { ProjectService } from '../../projects/services/projectService';
import { Project } from '../../../shared/types';

interface ProjectDeleteModalProps {
  project: Project | null;
  onClose: () => void;
}

export const ProjectDeleteModal: React.FC<ProjectDeleteModalProps> = ({
  project,
  onClose
}) => {
  const navigate = useNavigate();
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleConfirmDelete = async () => {
    if (!project?.id) return;
    
    try {
      setDeleteLoading(true);
      setDeleteError(null);
      
      await ProjectService.deleteProject(project.id);
      
      // Navigate back to home/project selection after successful deletion
      navigate('/');
    } catch (error: any) {
      console.error('Failed to delete project:', error);
      setDeleteError(error.message || 'Failed to delete project');
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleCancel = () => {
    setDeleteError(null);
    onClose();
  };

  if (!project) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="modal-backdrop fixed bg-black bg-opacity-50 z-[10000]"
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
        onClick={handleCancel}
      />

      {/* Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-[10001] p-4">
        <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
                <Trash2 className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Delete Project</h2>
                <p className="text-sm text-gray-500">This action cannot be undone</p>
              </div>
            </div>
            <button
              onClick={handleCancel}
              disabled={deleteLoading}
              className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <XIcon className="w-4 h-4 text-gray-500" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 space-y-4">
            {deleteError && (
              <div className="flex items-center p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
                <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
                <span>{deleteError}</span>
              </div>
            )}

            <div className="flex items-center p-3 bg-gray-50 border border-gray-200 rounded-lg">
              <Globe className="w-5 h-5 text-red-600 mr-3" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-700 truncate">{project.name}</p>
                <p className="text-sm text-gray-500 truncate">{project.default_start_url}</p>
              </div>
            </div>

            <div className="space-y-2 text-sm text-gray-600">
              <p className="font-medium text-red-800">This will permanently delete:</p>
              <ul className="list-disc list-inside space-y-1 ml-4">
                <li>The entire project and its configuration</li>
                <li>All test cases and their configurations</li>
                <li>All test runs and execution history</li>
                <li>All browser configurations</li>
                <li>All secret values</li>
                <li>All documents and traversals</li>
              </ul>
            </div>

            <p className="text-sm text-gray-600 font-medium">
              Are you absolutely sure you want to delete this project?
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200">
            <button
              type="button"
              onClick={handleCancel}
              disabled={deleteLoading}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirmDelete}
              disabled={deleteLoading}
              className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-lg hover:bg-red-700 focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {deleteLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>{deleteLoading ? 'Deleting...' : 'Delete Project'}</span>
            </button>
          </div>
        </div>
      </div>
    </>
  );
};
