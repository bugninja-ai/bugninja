import React from 'react';
import { Monitor, Plus, Trash2 } from 'lucide-react';
import { CustomDropdown } from '../../../shared/components/CustomDropdown';
import { BrowserConfigOptions, BrowserConfigData } from '../../settings/types';

interface BrowserConfigurationsSectionProps {
  newBrowserConfigs: {
    id: string;
    browserChannel: string;
    userAgent: string;
    viewportSize: { width: number; height: number };
    geolocation?: { latitude: number; longitude: number };
  }[];
  existingBrowserConfigIds: string[];
  existingBrowserConfigs: BrowserConfigData[];
  browserConfigOptions: BrowserConfigOptions | null;
  onNewBrowserConfigChange: (index: number, field: string, value: any) => void;
  onAddNewBrowserConfig: () => void;
  onRemoveNewBrowserConfig: (index: number) => void;
  onRemoveExistingBrowserConfig: (configId: string) => void;
  onAddExistingBrowserConfig: (configId: string) => void;
  browserChannelDropdowns: Record<string, boolean>;
  setBrowserChannelDropdowns: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
  userAgentDropdowns: Record<string, boolean>;
  setUserAgentDropdowns: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
  viewportDropdowns: Record<string, boolean>;
  setViewportDropdowns: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
  existingBrowserConfigDropdowns: Record<string, boolean>;
  setExistingBrowserConfigDropdowns: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
}

export const BrowserConfigurationsSection: React.FC<BrowserConfigurationsSectionProps> = ({
  newBrowserConfigs,
  existingBrowserConfigIds,
  existingBrowserConfigs,
  browserConfigOptions,
  onNewBrowserConfigChange,
  onAddNewBrowserConfig,
  onRemoveNewBrowserConfig,
  onRemoveExistingBrowserConfig,
  onAddExistingBrowserConfig,
  browserChannelDropdowns,
  setBrowserChannelDropdowns,
  userAgentDropdowns,
  setUserAgentDropdowns,
  viewportDropdowns,
  setViewportDropdowns,
  existingBrowserConfigDropdowns,
  setExistingBrowserConfigDropdowns,
}) => {
  const handleExistingConfigSelect = (configId: string) => {
    if (configId && !existingBrowserConfigIds.includes(configId)) {
      onAddExistingBrowserConfig(configId);
    }
  };

  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200 overflow-visible relative z-0">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800">Browser Configurations</h2>
        <button
          type="button"
          onClick={onAddNewBrowserConfig}
          className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
        >
          <Plus className="w-4 h-4 mr-1" />
          Add Config
        </button>
      </div>

      {/* Select Existing Browser Config */}
      {existingBrowserConfigs.length > 0 && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Or select an existing browser configuration
          </label>
          <CustomDropdown
            options={existingBrowserConfigs.map(config => {
              const viewport = config.browser_config?.viewport;
              const userAgent = config.browser_config?.user_agent || '';
              
              // Extract browser type from user agent 
              let browserType = 'Unknown';
              if (userAgent.includes('Chrome') && !userAgent.includes('Edg')) browserType = 'Chromium';
              else if (userAgent.includes('Firefox')) browserType = 'Firefox';
              else if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) browserType = 'Webkit';
              else if (userAgent.includes('Edg')) browserType = 'Microsoft Edge';
              
              return {
                value: config.id,
                label: `${browserType} - ${viewport?.width || 1920}×${viewport?.height || 1080}`
              };
            })}
            value=""
            onChange={handleExistingConfigSelect}
            isOpen={existingBrowserConfigDropdowns['main'] || false}
            setIsOpen={(open) => setExistingBrowserConfigDropdowns(prev => ({ ...prev, main: open }))}
            placeholder="Select existing configuration"
            fullWidth={true}
          />
        </div>
      )}

      <div className="space-y-4">
        {/* Existing Browser Configs (Non-editable) */}
        {existingBrowserConfigIds.map((configId) => {
          const config = existingBrowserConfigs.find(c => c.id === configId);
          if (!config) return null;
          
          const viewport = config.browser_config?.viewport;
          const userAgent = config.browser_config?.user_agent || '';
          
          // Extract browser type from user agent 
          let browserType = 'Unknown';
          if (userAgent.includes('Chrome') && !userAgent.includes('Edg')) browserType = 'Chromium';
          else if (userAgent.includes('Firefox')) browserType = 'Firefox';
          else if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) browserType = 'Webkit';
          else if (userAgent.includes('Edg')) browserType = 'Microsoft Edge';
          
          return (
            <div key={configId} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  <Monitor className="w-5 h-5 text-gray-600" />
                  <span className="text-sm font-medium text-gray-700">
                    {browserType} - {viewport?.width || 1920}×{viewport?.height || 1080} (Existing)
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => onRemoveExistingBrowserConfig(configId)}
                  className="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <div className="text-xs text-gray-500">
                This configuration will be reused from existing setup
              </div>
            </div>
          );
        })}

        {/* New Browser Configs (Editable) */}
        {newBrowserConfigs.map((config, index) => (
          <div key={config.id} className="border border-gray-200 rounded-lg p-4 overflow-visible">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <Monitor className="w-5 h-5 text-gray-600" />
                <span className="text-sm font-medium text-gray-700">New Browser Configuration</span>
              </div>
              <button
                type="button"
                onClick={() => onRemoveNewBrowserConfig(index)}
                className="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                title="Remove browser configuration"
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
                  onChange={(value) => onNewBrowserConfigChange(index, 'browserChannel', value)}
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
                  onChange={(value) => onNewBrowserConfigChange(index, 'userAgent', value)}
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
                  value={`${config.viewportSize.width}x${config.viewportSize.height}`}
                  onChange={(value) => {
                    const [width, height] = value.split('x').map(Number);
                    onNewBrowserConfigChange(index, 'viewportSize.width', width);
                    onNewBrowserConfigChange(index, 'viewportSize.height', height);
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
                  onChange={(e) => {
                    const value = e.target.value;
                    if (value) {
                      onNewBrowserConfigChange(index, 'geolocation.latitude', parseFloat(value));
                    } else {
                      onNewBrowserConfigChange(index, 'geolocation', undefined);
                    }
                  }}
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
                  onChange={(e) => {
                    const value = e.target.value;
                    if (value) {
                      onNewBrowserConfigChange(index, 'geolocation.longitude', parseFloat(value));
                    } else if (!config.geolocation?.latitude) {
                      onNewBrowserConfigChange(index, 'geolocation', undefined);
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                  placeholder="e.g. -74.0060"
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
