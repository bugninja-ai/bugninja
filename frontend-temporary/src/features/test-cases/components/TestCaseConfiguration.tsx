import React from 'react';
import { Globe, Plus, Trash2 } from 'lucide-react';
import { FrontendTestCase } from '../types';
import { EditableSection } from '../../../shared/components/EditableSection';

interface TestCaseConfigurationProps {
  testCase: FrontendTestCase;
  editableTestCase: FrontendTestCase | null;
  isEditing: boolean;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
  onStartingUrlChange: (url: string) => void;
  onAllowedDomainsChange: (domains: string[]) => void;
}

export const TestCaseConfiguration: React.FC<TestCaseConfigurationProps> = ({
  testCase,
  editableTestCase,
  isEditing,
  onEdit,
  onSave,
  onCancel,
  onStartingUrlChange,
  onAllowedDomainsChange
}) => {
  const addDomain = () => {
    if (editableTestCase) {
      const newDomains = [...editableTestCase.allowedDomains, ''];
      onAllowedDomainsChange(newDomains);
    }
  };

  const updateDomain = (index: number, value: string) => {
    if (editableTestCase) {
      const newDomains = [...editableTestCase.allowedDomains];
      newDomains[index] = value;
      onAllowedDomainsChange(newDomains);
    }
  };

  const removeDomain = (index: number) => {
    if (editableTestCase) {
      const newDomains = editableTestCase.allowedDomains.filter((_, i) => i !== index);
      onAllowedDomainsChange(newDomains);
    }
  };

  return (
    <EditableSection
      title="Test configuration"
      isEditing={isEditing}
      onEdit={onEdit}
      onSave={onSave}
      onCancel={onCancel}
      editTitle="Edit configuration"
    >
      <div className="space-y-6">
        {/* Starting URL */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Starting URL</label>
          {isEditing ? (
            <div className="flex items-center space-x-2">
              <Globe className="w-4 h-4 text-gray-400 ml-3" />
              <input
                type="url"
                value={editableTestCase?.startingUrl || ''}
                onChange={(e) => onStartingUrlChange(e.target.value)}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="Enter starting URL"
              />
            </div>
          ) : (
            <div className="flex items-center space-x-2 px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-800">
              <Globe className="w-4 h-4 text-gray-400" />
              <span className="break-all">{testCase.startingUrl}</span>
            </div>
          )}
        </div>

        {/* Allowed Domains */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">Allowed domains</label>
            {isEditing && (
              <button
                onClick={addDomain}
                className="inline-flex items-center px-3 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
              >
                <Plus className="w-4 h-4 mr-1" />
                Add domain
              </button>
            )}
          </div>
          <div className="space-y-2">
            {isEditing ? (
              editableTestCase?.allowedDomains.map((domain, index) => (
                <div key={index} className="flex items-center space-x-2">
                  <Globe className="w-4 h-4 text-gray-400 ml-3" />
                  <input
                    type="text"
                    value={domain}
                    onChange={(e) => updateDomain(index, e.target.value)}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="Enter domain"
                  />
                  <button
                    onClick={() => removeDomain(index)}
                    className="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            ) : (
              testCase.allowedDomains.map((domain, index) => (
                <div key={index} className="flex items-center space-x-2 px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-800">
                  <Globe className="w-4 h-4 text-gray-400" />
                  <span>{domain}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </EditableSection>
  );
};
