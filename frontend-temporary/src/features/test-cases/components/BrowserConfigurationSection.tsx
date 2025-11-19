import React, { Dispatch, SetStateAction } from 'react';
import { Monitor, Plus, Trash2, MapPin } from 'lucide-react';
import { FrontendTestCase, BrowserConfig } from '../types';
import { EditableSection } from '../../../shared/components/EditableSection';
import { CustomDropdown } from '../../../shared/components/CustomDropdown';
import { BrowserConfigOptions, BrowserConfigData } from '../../settings/types';

interface BrowserConfigurationSectionProps {
  testCase: FrontendTestCase;
  editableTestCase: FrontendTestCase | null;
  isEditing: boolean;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
  onConfigChange: (configs: BrowserConfig[]) => void;
  onExistingConfigAdd: (configIds: string[]) => void;
  browserConfigOptions: BrowserConfigOptions | null;
  existingBrowserConfigs: BrowserConfigData[];
  existingBrowserConfigDropdownOpen: boolean;
  setExistingBrowserConfigDropdownOpen: (open: boolean) => void;
  browserChannelDropdowns: Record<string, boolean>;
  setBrowserChannelDropdowns: Dispatch<SetStateAction<Record<string, boolean>>>;
  userAgentDropdowns: Record<string, boolean>;
  setUserAgentDropdowns: Dispatch<SetStateAction<Record<string, boolean>>>;
  viewportDropdowns: Record<string, boolean>;
  setViewportDropdowns: Dispatch<SetStateAction<Record<string, boolean>>>;
}

export const BrowserConfigurationSection: React.FC<BrowserConfigurationSectionProps> = ({
  testCase,
  editableTestCase,
  isEditing,
  onEdit,
  onSave,
  onCancel,
  onConfigChange,
  onExistingConfigAdd,
  browserConfigOptions,
  existingBrowserConfigs,
  existingBrowserConfigDropdownOpen,
  setExistingBrowserConfigDropdownOpen,
  browserChannelDropdowns,
  setBrowserChannelDropdowns,
  userAgentDropdowns,
  setUserAgentDropdowns,
  viewportDropdowns,
  setViewportDropdowns
}) => {
  const addNewConfig = () => {
    if (editableTestCase) {
      const newConfig: BrowserConfig = {
        id: `config-${Date.now()}`,
        browserChannel: '',
        userAgent: '',
        viewport: { width: 1920, height: 1080 },
        geolocation: undefined
      };
      onConfigChange([...editableTestCase.browserConfigs, newConfig]);
    }
  };

  const removeConfig = (index: number) => {
    if (editableTestCase) {
      const newConfigs = editableTestCase.browserConfigs.filter((_, i) => i !== index);
      onConfigChange(newConfigs);
    }
  };

  const updateConfig = (index: number, updates: Partial<BrowserConfig>) => {
    if (editableTestCase) {
      const newConfigs = [...editableTestCase.browserConfigs];
      newConfigs[index] = { ...newConfigs[index], ...updates };
      onConfigChange(newConfigs);
    }
  };

  const updateGeolocation = (index: number, field: 'latitude' | 'longitude', value: string) => {
    if (editableTestCase) {
      const newConfigs = [...editableTestCase.browserConfigs];
      const config = newConfigs[index];
      
      if (value) {
        newConfigs[index] = {
          ...config,
          geolocation: {
            latitude: field === 'latitude' ? parseFloat(value) : (config.geolocation?.latitude || 0),
            longitude: field === 'longitude' ? parseFloat(value) : (config.geolocation?.longitude || 0)
          }
        };
      } else if (!config.geolocation?.[field === 'latitude' ? 'longitude' : 'latitude']) {
        newConfigs[index] = { ...config, geolocation: undefined };
      }
      
      onConfigChange(newConfigs);
    }
  };

  const handleExistingConfigSelect = (configId: string) => {
    if (configId && editableTestCase) {
      const currentIds = editableTestCase.existingBrowserConfigIds || [];
      if (!currentIds.includes(configId)) {
        onExistingConfigAdd([...currentIds, configId]);
      }
    }
  };

  const removeExistingConfig = (configId: string) => {
    if (editableTestCase && editableTestCase.existingBrowserConfigIds) {
      const updatedIds = editableTestCase.existingBrowserConfigIds.filter(id => id !== configId);
      onExistingConfigAdd(updatedIds);
    }
  };

  const getBrowserChannelDisplay = (config: BrowserConfigData) => {
    // Prefer browser_channel field, then extract from user agent
    if (config.browser_config?.browser_channel) {
      return config.browser_config.browser_channel;
    }
    
    const userAgent = config.browser_config?.user_agent || '';
    if (userAgent.includes('Chrome') && !userAgent.includes('Edg')) return 'Chromium';
    if (userAgent.includes('Firefox')) return 'Firefox';
    if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) return 'Webkit';
    if (userAgent.includes('Edg')) return 'Microsoft Edge';
    return 'Unknown';
  };

  return (
    <EditableSection
      title="Browser configurations"
      isEditing={isEditing}
      onEdit={onEdit}
      onSave={onSave}
      onCancel={onCancel}
      editTitle="Edit browser configurations"
    >
      {/* Select Existing Browser Config - Only show in edit mode */}
      {isEditing && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Or select an existing browser configuration
          </label>
          
          {existingBrowserConfigs.length === 0 ? (
            <div className="text-sm text-gray-500 italic">
              No existing browser configurations found for this project
            </div>
          ) : (
            <CustomDropdown
              options={existingBrowserConfigs
                .filter(config => !editableTestCase?.existingBrowserConfigIds?.includes(config.id))
                .map(config => {
                  const viewport = config.browser_config?.viewport;
                  const browserType = getBrowserChannelDisplay(config);
                  
                  return {
                    value: config.id,
                    label: `${browserType} - ${viewport?.width || 1920}×${viewport?.height || 1080}`
                  };
                })}
              value=""
              onChange={handleExistingConfigSelect}
              isOpen={existingBrowserConfigDropdownOpen}
              setIsOpen={setExistingBrowserConfigDropdownOpen}
              placeholder="Select existing configuration"
              fullWidth={true}
            />
          )}
        </div>
      )}
      
      <div className="space-y-4">
        {isEditing ? (
          <>
            {/* Existing Browser Configurations (Non-editable) - Linked from project */}
            {editableTestCase?.existingBrowserConfigIds?.map((configId) => {
              const config = existingBrowserConfigs.find(c => c.id === configId);
              if (!config) return null;
              
              const viewport = config.browser_config?.viewport;
              const browserChannel = getBrowserChannelDisplay(config);
              const userAgent = config.browser_config?.user_agent || 'Not specified';
              
              return (
                <div key={configId} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      <Monitor className="w-5 h-5 text-gray-400" />
                      <span className="font-medium text-gray-700">{browserChannel} (Existing)</span>
                    </div>
                    <button
                      onClick={() => removeExistingConfig(configId)}
                      className="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Browser Channel</label>
                      <div className="px-3 py-2 bg-white border border-gray-200 rounded text-gray-600">
                        {browserChannel}
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Viewport</label>
                      <div className="px-3 py-2 bg-white border border-gray-200 rounded text-gray-600">
                        {viewport?.width || 1920} × {viewport?.height || 1080}
                      </div>
                    </div>
                    
                    <div className="md:col-span-2">
                      <label className="block text-xs font-medium text-gray-500 mb-1">User Agent</label>
                      <div className="px-3 py-2 bg-white border border-gray-200 rounded text-gray-600 font-mono text-xs break-all">
                        {userAgent.length > 80 ? `${userAgent.slice(0, 80)}...` : userAgent}
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-2 text-xs text-gray-500">
                    This configuration will be reused from existing setup
                  </div>
                </div>
              );
            })}

            {/* New Browser Configurations (Editable) */}
            {editableTestCase?.browserConfigs.map((config, index) => (
              <div key={config.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <Monitor className="w-5 h-5 text-gray-400" />
                    <span className="font-medium text-gray-800">Browser Configuration</span>
                  </div>
                  <button
                    onClick={() => removeConfig(index)}
                    className="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm overflow-visible">
                  <div className="md:col-span-2">
                    <label className="block text-xs font-medium text-gray-500 mb-1">Browser Channel</label>
                    <CustomDropdown
                      options={browserConfigOptions?.browser_channels.map(channel => ({ value: channel, label: channel })) || []}
                      value={config.browserChannel || ''}
                      onChange={(value) => updateConfig(index, { browserChannel: value })}
                      isOpen={browserChannelDropdowns[config.id] || false}
                      setIsOpen={(open) => setBrowserChannelDropdowns(prev => ({ ...prev, [config.id]: open }))}
                      placeholder="Select Browser Channel"
                      fullWidth={true}
                    />
                  </div>
                  
                  <div className="md:col-span-2">
                    <label className="block text-xs font-medium text-gray-500 mb-1">User Agent</label>
                    <CustomDropdown
                      options={browserConfigOptions?.user_agents.map(agent => ({ value: agent, label: agent.slice(0, 50) + '...' })) || []}
                      value={config.userAgent || ''}
                      onChange={(value) => updateConfig(index, { userAgent: value })}
                      isOpen={userAgentDropdowns[config.id] || false}
                      setIsOpen={(open) => setUserAgentDropdowns(prev => ({ ...prev, [config.id]: open }))}
                      placeholder="Select User Agent"
                      fullWidth={true}
                    />
                  </div>
                  
                  <div className="md:col-span-2">
                    <label className="block text-xs font-medium text-gray-500 mb-1">Viewport Size</label>
                    <CustomDropdown
                      options={browserConfigOptions?.viewport_sizes.map(viewport => ({
                        value: `${viewport.width}x${viewport.height}`,
                        label: `${viewport.width} × ${viewport.height}`
                      })) || []}
                      value={config.viewport ? `${config.viewport.width}x${config.viewport.height}` : ''}
                      onChange={(value) => {
                        const [width, height] = value.split('x').map(Number);
                        updateConfig(index, { viewport: { width, height } });
                      }}
                      isOpen={viewportDropdowns[config.id] || false}
                      setIsOpen={(open) => setViewportDropdowns(prev => ({ ...prev, [config.id]: open }))}
                      placeholder="Select Viewport Size"
                      fullWidth={true}
                    />
                  </div>
                  
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Latitude (optional)</label>
                    <input
                      type="number"
                      step="any"
                      value={config.geolocation?.latitude || ''}
                      onChange={(e) => updateGeolocation(index, 'latitude', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                      placeholder="e.g. 40.7128"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Longitude (optional)</label>
                    <input
                      type="number"
                      step="any"
                      value={config.geolocation?.longitude || ''}
                      onChange={(e) => updateGeolocation(index, 'longitude', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                      placeholder="e.g. -74.0060"
                    />
                  </div>
                </div>
              </div>
            ))}
            
            <button
              onClick={addNewConfig}
              className="w-full py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-indigo-300 hover:text-indigo-600 transition-colors flex items-center justify-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span>Add browser configuration</span>
            </button>
          </>
        ) : (
          testCase.browserConfigs.map((config) => (
            <div key={config.id} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-3">
                <Monitor className="w-5 h-5 text-gray-400" />
                <h3 className="font-medium text-gray-800">Browser Configuration</h3>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Browser Channel</label>
                  <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded text-gray-700">
                    {config.browserChannel || 'No browser channel specified'}
                  </div>
                </div>
                
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Viewport</label>
                  <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded text-gray-700">
                    {config.viewport ? `${config.viewport.width} × ${config.viewport.height}` : 'No viewport specified'}
                  </div>
                </div>
                
                {config.geolocation && 
                 config.geolocation.latitude !== undefined && 
                 config.geolocation.longitude !== undefined && (
                  <div className="md:col-span-2">
                    <label className="block text-xs font-medium text-gray-500 mb-1">Geolocation</label>
                    <div className="flex items-center space-x-2 px-3 py-2 bg-gray-50 border border-gray-200 rounded text-gray-700">
                      <MapPin className="w-4 h-4 text-gray-400" />
                      <span>{config.geolocation.latitude}, {config.geolocation.longitude}</span>
                    </div>
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
