import React from 'react';
import { Globe, Plus, Trash2 } from 'lucide-react';

interface TestConfigurationSectionProps {
  formData: {
    startingUrl: string;
    allowedDomains: string[];
  };
  onInputChange: (field: string, value: string) => void;
  onDomainChange: (index: number, value: string) => void;
  onAddDomain: () => void;
  onRemoveDomain: (index: number) => void;
}

export const TestConfigurationSection: React.FC<TestConfigurationSectionProps> = ({
  formData,
  onInputChange,
  onDomainChange,
  onAddDomain,
  onRemoveDomain
}) => {
  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200 relative z-0">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Test Configuration</h2>
      
      <div className="space-y-6">
        {/* Starting URL */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Starting URL *</label>
          <div className="flex items-center space-x-2">
            <Globe className="w-4 h-4 text-gray-400 ml-3" />
            <input
              type="url"
              required
              value={formData.startingUrl}
              onChange={(e) => onInputChange('startingUrl', e.target.value)}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
              placeholder="https://example.com"
            />
          </div>
        </div>

        {/* Allowed Domains */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">Allowed Domains *</label>
            <button
              type="button"
              onClick={onAddDomain}
              className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
            >
              <Plus className="w-4 h-4 mr-1" />
              Add Domain
            </button>
          </div>
          <div className="space-y-2">
            {formData.allowedDomains.map((domain, index) => (
              <div key={index} className="flex items-center space-x-2">
                <Globe className="w-4 h-4 text-gray-400 ml-3" />
                <input
                  type="text"
                  value={domain}
                  onChange={(e) => onDomainChange(index, e.target.value)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                  placeholder="example.com"
                />
                {formData.allowedDomains.length > 1 && (
                  <button
                    type="button"
                    onClick={() => onRemoveDomain(index)}
                    className="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
