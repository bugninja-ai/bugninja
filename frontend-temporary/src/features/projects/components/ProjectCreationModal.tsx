import React, { useState } from 'react';
import { X, AlertCircle, Loader2, FolderPlus } from 'lucide-react';

interface ProjectCreationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateProject: (projectData: { name: string; default_start_url: string }) => Promise<void>;
  loading?: boolean;
}

export const ProjectCreationModal: React.FC<ProjectCreationModalProps> = ({
  isOpen,
  onClose,
  onCreateProject,
  loading = false,
}) => {
  const [formData, setFormData] = useState({
    name: '',
    default_start_url: '',
  });
  const [errors, setErrors] = useState<{ name?: string; default_start_url?: string }>({});

  const validateForm = () => {
    const newErrors: { name?: string; default_start_url?: string } = {};
    
    if (!formData.name.trim()) {
      newErrors.name = 'Project name is required';
    } else if (formData.name.trim().length < 3) {
      newErrors.name = 'Project name must be at least 3 characters';
    }
    
    if (!formData.default_start_url.trim()) {
      newErrors.default_start_url = 'Default start URL is required';
    } else if (!isValidUrl(formData.default_start_url.trim())) {
      newErrors.default_start_url = 'Please enter a valid URL (e.g., https://example.com)';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const isValidUrl = (url: string): boolean => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    try {
      await onCreateProject({
        name: formData.name.trim(),
        default_start_url: formData.default_start_url.trim(),
      });
      
      // Reset form and close modal on success
      setFormData({ name: '', default_start_url: '' });
      setErrors({});
      onClose();
    } catch (error) {
      console.error('Failed to create project:', error);
      // Error is handled by the parent component
    }
  };

  const handleClose = () => {
    setFormData({ name: '', default_start_url: '' });
    setErrors({});
    onClose();
  };

  if (!isOpen) return null;

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
        onClick={handleClose}
      />
      
      {/* Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-[10001] p-4">
        <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
                <FolderPlus className="w-5 h-5 text-indigo-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Create New Project</h2>
                <p className="text-sm text-gray-500">Set up a new testing project with its starting URL</p>
              </div>
            </div>
            <button
              onClick={handleClose}
              disabled={loading}
              className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <X className="w-4 h-4 text-gray-500" />
            </button>
          </div>
          
          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {/* Project Name */}
            <div>
              <label htmlFor="project-name" className="block text-sm font-medium text-gray-700 mb-2">
                Project Name *
              </label>
              <input
                id="project-name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="e.g., E-commerce Testing"
                disabled={loading}
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed ${
                  errors.name ? 'border-red-300' : 'border-gray-300'
                }`}
              />
              {errors.name && (
                <div className="flex items-center mt-1 text-sm text-red-600">
                  <AlertCircle className="w-4 h-4 mr-1" />
                  {errors.name}
                </div>
              )}
            </div>
            
            {/* Default Start URL */}
            <div>
              <label htmlFor="default-start-url" className="block text-sm font-medium text-gray-700 mb-2">
                Default Start URL *
              </label>
              <input
                id="default-start-url"
                type="url"
                value={formData.default_start_url}
                onChange={(e) => setFormData(prev => ({ ...prev, default_start_url: e.target.value }))}
                placeholder="https://example.com"
                disabled={loading}
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed ${
                  errors.default_start_url ? 'border-red-300' : 'border-gray-300'
                }`}
              />
              {errors.default_start_url && (
                <div className="flex items-center mt-1 text-sm text-red-600">
                  <AlertCircle className="w-4 h-4 mr-1" />
                  {errors.default_start_url}
                </div>
              )}
            </div>
            
            {/* Actions */}
            <div className="flex items-center justify-end space-x-3 pt-4">
              <button
                type="button"
                onClick={handleClose}
                disabled={loading}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-lg hover:bg-indigo-700 focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                <span>{loading ? 'Creating...' : 'Create Project'}</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
};