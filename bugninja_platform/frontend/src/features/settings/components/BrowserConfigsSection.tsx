import React, { useState, useEffect } from 'react';
import { Monitor, Trash2, Loader2 } from 'lucide-react';
import { useProjects } from '../../../shared/hooks/useProjects';
import { settingsService, BrowserConfig } from '../services/settingsService';
import { DeleteConfirmationModal } from '../../../shared/components/DeleteConfirmationModal';

export const BrowserConfigsSection: React.FC = () => {
  const { selectedProject } = useProjects();
  const [browserConfigs, setBrowserConfigs] = useState<BrowserConfig[]>([]);
  const [loading, setLoading] = useState(false);
  
  // Confirmation modal state
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    item: BrowserConfig | null;
    loading: boolean;
    error: string | null;
  }>({
    isOpen: false,
    item: null,
    loading: false,
    error: null,
  });

  // Fetch browser configs when project changes
  useEffect(() => {
    if (selectedProject?.id) {
      fetchBrowserConfigs();
    }
  }, [selectedProject?.id]);

  const fetchBrowserConfigs = async () => {
    if (!selectedProject?.id) return;
    
    setLoading(true);
    try {
      const data = await settingsService.getBrowserConfigs(selectedProject.id);
      // Filter out any configs with null browser_config to prevent errors
      const validConfigs = data.filter(config => config.browser_config !== null);
      setBrowserConfigs(validConfigs);
    } catch (err) {
      console.error('Error fetching browser configs:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteBrowserConfig = async (config: BrowserConfig) => {
    setConfirmModal({
      isOpen: true,
      item: config,
      loading: false,
      error: null,
    });
  };

  const confirmDelete = async () => {
    if (!confirmModal.item) return;

    setConfirmModal(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const result = await settingsService.deleteBrowserConfig(confirmModal.item.id);

      if (!result.success) {
        setConfirmModal(prev => ({ ...prev, error: result.error || 'Failed to delete browser configuration', loading: false }));
        return;
      }

      // Refresh the list
      await fetchBrowserConfigs();
      
      // Close modal on success
      setConfirmModal({
        isOpen: false,
        item: null,
        loading: false,
        error: null,
      });
    } catch (err) {
      setConfirmModal(prev => ({ ...prev, error: 'Failed to delete browser configuration', loading: false }));
      console.error('Error deleting browser config:', err);
    }
  };

  const formatBrowserConfig = (browserConfig: BrowserConfig) => {
    const config = browserConfig.browser_config;
    if (!config) return 'Default configuration';
    
    const parts = [];
    if (config.browser_channel) parts.push(config.browser_channel);
    if (config.viewport) parts.push(`${config.viewport.width}x${config.viewport.height}`);
    return parts.join(', ') || 'Default configuration';
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Browser Configurations</h2>
          <p className="text-gray-600">Manage browser configurations for your test cases</p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
          <span className="ml-2 text-gray-600">Loading browser configurations...</span>
        </div>
      ) : browserConfigs.length === 0 ? (
        <div className="text-center py-12">
          <Monitor className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Browser Configurations</h3>
          <p className="text-gray-600">Create test cases to automatically generate browser configurations.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {browserConfigs.map((config) => (
            <div key={config.id} className="bg-white p-4 rounded-lg border border-gray-200 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Monitor className="w-5 h-5 text-gray-500" />
                <div>
                  <h3 className="font-medium text-gray-900">{formatBrowserConfig(config)}</h3>
                  <p className="text-sm text-gray-600">Created {new Date(config.created_at).toLocaleDateString()}</p>
                </div>
              </div>
              <button
                onClick={() => handleDeleteBrowserConfig(config)}
                className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                title="Delete browser configuration"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <DeleteConfirmationModal
        isOpen={confirmModal.isOpen}
        onClose={() => setConfirmModal(prev => ({ ...prev, isOpen: false, error: null }))}
        onConfirm={confirmDelete}
        type="browser-config"
        itemName={
          confirmModal.item?.browser_config 
            ? formatBrowserConfig(confirmModal.item)
            : 'Default configuration'
        }
        loading={confirmModal.loading}
        error={confirmModal.error}
      />
    </div>
  );
};
