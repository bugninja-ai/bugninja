import React, { useState, useEffect } from 'react';
import { Key, Trash2, Loader2, Eye, EyeOff } from 'lucide-react';
import { useProjects } from '../../../shared/hooks/useProjects';
import { settingsService, SecretValue } from '../services/settingsService';
import { DeleteConfirmationModal } from '../../../shared/components/DeleteConfirmationModal';

export const SecretValuesSection: React.FC = () => {
  const { selectedProject } = useProjects();
  const [secretValues, setSecretValues] = useState<SecretValue[]>([]);
  const [loading, setLoading] = useState(false);
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  
  // Confirmation modal state
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    item: SecretValue | null;
    loading: boolean;
    error: string | null;
  }>({
    isOpen: false,
    item: null,
    loading: false,
    error: null,
  });

  // Fetch secret values when project changes
  useEffect(() => {
    if (selectedProject?.id) {
      fetchSecretValues();
    }
  }, [selectedProject?.id]);

  const fetchSecretValues = async () => {
    if (!selectedProject?.id) return;
    
    setLoading(true);
    try {
      const data = await settingsService.getSecretValues(selectedProject.id);
      setSecretValues(data);
    } catch (err) {
      console.error('Error fetching secret values:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSecretValue = async (secret: SecretValue) => {
    setConfirmModal({
      isOpen: true,
      item: secret,
      loading: false,
      error: null,
    });
  };

  const confirmDelete = async () => {
    if (!confirmModal.item) return;

    setConfirmModal(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const result = await settingsService.deleteSecretValue(confirmModal.item.id);

      if (!result.success) {
        setConfirmModal(prev => ({ ...prev, error: result.error || 'Failed to delete secret value', loading: false }));
        return;
      }

      // Refresh the list
      await fetchSecretValues();
      
      // Close modal on success
      setConfirmModal({
        isOpen: false,
        item: null,
        loading: false,
        error: null,
      });
    } catch (err) {
      setConfirmModal(prev => ({ ...prev, error: 'Failed to delete secret value', loading: false }));
      console.error('Error deleting secret value:', err);
    }
  };

  const toggleSecretVisibility = (secretId: string) => {
    setShowSecrets(prev => ({
      ...prev,
      [secretId]: !prev[secretId]
    }));
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Secret Values</h2>
          <p className="text-gray-600">Manage secret values used in your test cases</p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
          <span className="ml-2 text-gray-600">Loading secret values...</span>
        </div>
      ) : secretValues.length === 0 ? (
        <div className="text-center py-12">
          <Key className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Secret Values</h3>
          <p className="text-gray-600">Create test cases with secrets to see them listed here.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {secretValues.map((secret) => (
            <div key={secret.id} className="bg-white p-4 rounded-lg border border-gray-200 flex items-center justify-between">
              <div className="flex items-center space-x-3 flex-1">
                <Key className="w-5 h-5 text-gray-500" />
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-gray-900 truncate">{secret.secret_name}</h3>
                  <div className="flex items-start space-x-2">
                    <p className={`text-sm text-gray-600 font-mono flex-1 ${
                      showSecrets[secret.id] ? 'break-all' : 'truncate'
                    }`}>
                      {showSecrets[secret.id] 
                        ? secret.secret_value 
                        : '•'.repeat(Math.min(secret.secret_value.length, 16))
                      }
                    </p>
                    <button
                      onClick={() => toggleSecretVisibility(secret.id)}
                      className="p-1 text-gray-500 hover:text-gray-700 transition-colors flex-shrink-0 mt-0.5"
                      title={showSecrets[secret.id] ? 'Hide secret' : 'Show secret'}
                    >
                      {showSecrets[secret.id] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  <p className="text-xs text-gray-500">Created {new Date(secret.created_at).toLocaleDateString()}</p>
                </div>
              </div>
              <button
                onClick={() => handleDeleteSecretValue(secret)}
                className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors ml-2"
                title="Delete secret value"
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
        type="secret-value"
        itemName={confirmModal.item?.secret_name || ''}
        loading={confirmModal.loading}
        error={confirmModal.error}
      />
    </div>
  );
};
