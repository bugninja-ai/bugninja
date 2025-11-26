import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { CustomDropdown } from '../../../shared/components/CustomDropdown';
import { SecretValue } from '../../settings/types';

interface SecretsSectionProps {
  newSecrets: { id: string; secretName: string; value: string; }[];
  existingSecretIds: string[];
  existingSecrets: SecretValue[];
  onNewSecretChange: (index: number, field: string, value: string) => void;
  onAddNewSecret: () => void;
  onRemoveNewSecret: (index: number) => void;
  onRemoveExistingSecret: (secretId: string) => void;
  onAddExistingSecret: (secretId: string) => void;
  existingSecretsDropdowns: Record<string, boolean>;
  setExistingSecretsDropdowns: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
}

export const SecretsSection: React.FC<SecretsSectionProps> = ({
  newSecrets,
  existingSecretIds,
  existingSecrets,
  onNewSecretChange,
  onAddNewSecret,
  onRemoveNewSecret,
  onRemoveExistingSecret,
  onAddExistingSecret,
  existingSecretsDropdowns,
  setExistingSecretsDropdowns
}) => {
  const handleExistingSecretSelect = (secretId: string) => {
    if (secretId && !existingSecretIds.includes(secretId)) {
      onAddExistingSecret(secretId);
    }
  };

  return (
    <div className="bg-white rounded-lg p-6 border border-gray-200">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800">Secrets</h2>
        <button
          type="button"
          onClick={onAddNewSecret}
          className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
        >
          <Plus className="w-4 h-4 mr-1" />
          Add Secret
        </button>
      </div>

      {/* Select Existing Secret */}
      {existingSecrets.length > 0 && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Or select an existing secret
          </label>
          <CustomDropdown
            options={existingSecrets.map(secret => ({
              value: secret.id,
              label: `${secret.secret_name} - ${new Date(secret.created_at).toLocaleDateString()}`
            }))}
            value=""
            onChange={handleExistingSecretSelect}
            isOpen={existingSecretsDropdowns['main'] || false}
            setIsOpen={(open) => setExistingSecretsDropdowns(prev => ({ ...prev, main: open }))}
            placeholder="Select existing secret"
            fullWidth={true}
          />
        </div>
      )}
        
      <div className="space-y-3">
        {/* Existing Secrets (Non-editable) */}
        {existingSecretIds.map((secretId) => {
          const secret = existingSecrets.find(s => s.id === secretId);
          if (!secret) return null;
          
          return (
            <div key={secretId} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
              <div className="flex items-center justify-between mb-2">
                <span className="flex-1 text-sm font-medium text-gray-700 mr-4">
                  {secret.secret_name} (Existing)
                </span>
                <button
                  type="button"
                  onClick={() => onRemoveExistingSecret(secretId)}
                  className="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <div className="text-xs text-gray-500">
                This secret will be reused from existing setup
              </div>
            </div>
          );
        })}

        {/* New Secrets (Editable) */}
        {newSecrets.map((secret, index) => (
          <div key={secret.id} className="border border-gray-200 rounded-lg p-4 overflow-visible">
            <div className="flex items-center justify-between mb-2">
              <input
                type="text"
                value={secret.secretName}
                onChange={(e) => onNewSecretChange(index, 'secretName', e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white text-sm mr-4"
                placeholder="Secret name"
              />
              <button
                type="button"
                onClick={() => onRemoveNewSecret(index)}
                className="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
            
            <div>
              <input
                type="password"
                value={secret.value}
                onChange={(e) => onNewSecretChange(index, 'value', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded text-gray-800 font-mono text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                placeholder="Secret value"
              />
            </div>
          </div>
        ))}
      </div>

      {/* Add Secrets Button - Show when no secrets exist */}
      {newSecrets.length === 0 && existingSecretIds.length === 0 && (
        <div className="text-center mt-4">
          <button
            type="button"
            onClick={onAddNewSecret}
            className="inline-flex items-center px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
          >
            <Plus className="w-4 h-4 mr-1" />
            Add Secrets (Optional)
          </button>
        </div>
      )}
    </div>
  );
};
