import React from 'react';
import { MonitorPlay } from 'lucide-react';
import { TestRun } from '../../test-runs/types';

interface BrowserConfigurationProps {
  testRun: TestRun;
}

export const BrowserConfiguration: React.FC<BrowserConfigurationProps> = ({ testRun }) => {
  const getBrowserInfo = (run: TestRun) => {
    const browserConfig = run.testCase.browserConfigs.find(config => 
      config.userAgent === run.userAgent || 
      config.browserChannel.toLowerCase().includes(run.browser.toLowerCase().split(' ')[0])
    );
    
    if (browserConfig) {
      return browserConfig;
    }
    
    return {
      id: 'default',
      browserChannel: run.browser,
      userAgent: run.userAgent,
      viewport: { width: 1920, height: 1080 }
    };
  };

  const browserInfo = getBrowserInfo(testRun);

  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Browser configuration</h2>
      <div className="border border-gray-200 rounded-lg p-4">
        <div className="flex items-center space-x-2 mb-3">
          <MonitorPlay className="w-5 h-5 text-gray-600" />
          <h3 className="font-medium text-gray-800">{browserInfo.browserChannel}</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">User agent</label>
            <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded text-gray-700 text-xs break-all">
              {browserInfo.userAgent}
            </div>
          </div>
          
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Viewport</label>
            <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded text-gray-700">
              {browserInfo.viewport.width} × {browserInfo.viewport.height}
            </div>
          </div>
          
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Environment</label>
            <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded text-gray-700 capitalize">
              {testRun.environment}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
