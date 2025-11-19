import React from 'react';
import { Plus, Trash2, Eye, EyeOff, Copy, CheckCircle } from 'lucide-react';
import { FrontendTestCase, TestSecret } from '../types';
import { EditableSection } from '../../../shared/components/EditableSection';
import { CustomDropdown } from '../../../shared/components/CustomDropdown';
import { SecretValue } from '../../settings/types';

interface SecretsSectionProps {
  testCase: FrontendTestCase;
  editableTestCase: FrontendTestCase | null;
  isEditing: boolean;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
  onSecretsChange: (secrets: TestSecret[]) => void;
  onExistingSecretsAdd: (secretIds: string[]) => void;
  existingSecrets: SecretValue[];
  existingSecretDropdownOpen: boolean;
  setExistingSecretDropdownOpen: (open: boolean) => void;
  visibleSecrets: Set<string>;
  onToggleSecretVisibility: (secretId: string) => void;
  copiedSecret: string | null;
  onCopySecret: (value: string, secretId: string) => void;
}

export const SecretsSection: React.FC<SecretsSectionProps> = ({
  testCase,
  editableTestCase,
  isEditing,
  onEdit,
  onSave,
  onCancel,
  onSecretsChange,
  onExistingSecretsAdd,
  existingSecrets,
  existingSecretDropdownOpen,
  setExistingSecretDropdownOpen,
  visibleSecrets,
  onToggleSecretVisibility,
  copiedSecret,
  onCopySecret
}) => {
  const addNewSecret = () => {
    if (editableTestCase) {
      const newSecret: TestSecret = {
        id: `secret-${Date.now()}`,
        secretName: '',
        value: ''
      };
      onSecretsChange([...editableTestCase.secrets, newSecret]);
    }
  };

  const removeSecret = (index: number) => {
    if (editableTestCase) {
      const newSecrets = editableTestCase.secrets.filter((_, i) => i !== index);
      onSecretsChange(newSecrets);
    }
  };

  const updateSecret = (index: number, field: keyof TestSecret, value: string) => {
    if (editableTestCase) {
      const newSecrets = [...editableTestCase.secrets];
      newSecrets[index] = { ...newSecrets[index], [field]: value };
      onSecretsChange(newSecrets);
    }
  };

  const handleExistingSecretSelect = (secretId: string) => {
    if (secretId && editableTestCase) {
      const currentIds = editableTestCase.existingSecretIds || [];
      if (!currentIds.includes(secretId)) {
        onExistingSecretsAdd([...currentIds, secretId]);
      }
    }
  };

  const removeExistingSecret = (secretId: string) => {
    if (editableTestCase && editableTestCase.existingSecretIds) {
      const updatedIds = editableTestCase.existingSecretIds.filter(id => id !== secretId);
      onExistingSecretsAdd(updatedIds);
    }
  };

  // Only show section if there are secrets or we're editing
  if (testCase.secrets.length === 0 && !isEditing) {
    return null;
  }

  return (
    <EditableSection
      title="Secrets"
      isEditing={isEditing}
      onEdit={onEdit}
      onSave={onSave}
      onCancel={onCancel}
      editTitle="Edit secrets"
    >
      {/* Select Existing Secret - Only show in edit mode */}
      {isEditing && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Or select an existing secret
          </label>
          
          {existingSecrets.length === 0 ? (
            <div className="text-sm text-gray-500 italic">
              No existing secrets found for this project
            </div>
          ) : (
            <CustomDropdown
              options={existingSecrets
                .filter(secret => !editableTestCase?.secrets.some(existing => existing.id === secret.id))
                .map(secret => ({
                  value: secret.id,
                  label: `${secret.secret_name} - ${new Date(secret.created_at).toLocaleDateString()}`
                }))}
              value=""
              onChange={handleExistingSecretSelect}
              isOpen={existingSecretDropdownOpen}
              setIsOpen={setExistingSecretDropdownOpen}
              placeholder="Select existing secret"
              fullWidth={true}
            />
          )}
        </div>
      )}
      
      <div className="space-y-4">
        {isEditing ? (
          <>
            {/* Existing Secrets (Non-editable) - Linked from project */}
            {editableTestCase?.existingSecretIds?.map((secretId) => {
              const secret = existingSecrets.find(s => s.id === secretId);
              if (!secret) return null;
              
              return (
                <div key={secretId} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                  <div className="flex items-center justify-between mb-2">
                    <span className="flex-1 text-sm font-medium text-gray-700 mr-4">
                      {secret.secret_name} (Existing)
                    </span>
                    <button
                      onClick={() => removeExistingSecret(secretId)}
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
            {editableTestCase?.secrets.map((secret, index) => (
              <div key={secret.id} className="border border-gray-200 rounded-lg p-4 overflow-visible">
                <div className="flex items-center justify-between mb-2">
                  <input
                    type="text"
                    value={secret.secretName}
                    onChange={(e) => updateSecret(index, 'secretName', e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white text-sm mr-4"
                    placeholder="Secret name"
                  />
                  <button
                    type="button"
                    onClick={() => removeSecret(index)}
                    className="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                
                <div>
                  <input
                    type="password"
                    value={secret.value}
                    onChange={(e) => updateSecret(index, 'value', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded text-gray-800 font-mono text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                    placeholder="Secret value"
                  />
                </div>
              </div>
            ))}

            <button
              onClick={addNewSecret}
              className="w-full py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-indigo-300 hover:text-indigo-600 transition-colors flex items-center justify-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span>Add secret</span>
            </button>
          </>
        ) : (
          testCase.secrets.map((secret) => (
            <div key={secret.id} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700">{secret.secretName}</label>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => onToggleSecretVisibility(secret.id)}
                    className="p-1 text-gray-400 hover:text-gray-600 rounded transition-colors"
                    title={visibleSecrets.has(secret.id) ? 'Hide value' : 'Show value'}
                  >
                    {visibleSecrets.has(secret.id) ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                  <button
                    onClick={() => onCopySecret(secret.value, secret.id)}
                    className="p-1 text-gray-400 hover:text-gray-600 rounded transition-colors"
                    title="Copy to clipboard"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              <div className="relative">
                <input
                  type={visibleSecrets.has(secret.id) ? 'text' : 'password'}
                  value={secret.value}
                  readOnly
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded text-gray-800 font-mono text-sm"
                />
                {copiedSecret === secret.id && (
                  <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex items-center space-x-1 text-emerald-600 text-xs">
                    <CheckCircle className="w-3 h-3" />
                    <span>Copied!</span>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </EditableSection>
  );
};
