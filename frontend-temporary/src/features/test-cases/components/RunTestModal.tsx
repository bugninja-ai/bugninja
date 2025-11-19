import React, { useState } from 'react';
import { X, Play, Monitor, Loader2, RotateCcw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { FrontendTestCase, BrowserConfig } from '../types';
import { TestCaseService } from '../services/testCaseService';

interface RunTestModalProps {
  isOpen: boolean;
  onClose: () => void;
  testCase: FrontendTestCase | null;
  onTestStarted?: (testRunId: string) => void;
}

export const RunTestModal: React.FC<RunTestModalProps> = ({
  isOpen,
  onClose,
  testCase,
  onTestStarted,
}) => {
  const navigate = useNavigate();
  const [runningConfigs, setRunningConfigs] = useState<Set<string>>(new Set());
  const [replayingConfigs, setReplayingConfigs] = useState<Set<string>>(new Set());
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [replayAvailability, setReplayAvailability] = useState<Record<string, boolean>>({});

  const handleRunConfiguration = async (browserConfig: BrowserConfig) => {
    if (!testCase) return;
    
    setExecutionError(null);
    setRunningConfigs(prev => new Set(prev).add(browserConfig.id));

    try {
      const result = await TestCaseService.executeTestConfiguration(testCase.id, browserConfig.id);
      
      if (onTestStarted && result?.id) {
        onTestStarted(result.id);
      }
      
      // Close modal and redirect to test run page
      onClose();
      setRunningConfigs(new Set());
      setReplayingConfigs(new Set());
      
      // Navigate to the test run detail page
      if (result?.id) {
        navigate(`/runs/${result.id}`);
      }
    } catch (error: any) {
      console.error('Failed to execute test configuration:', error);
      setExecutionError(error.message || 'Failed to start test execution');
    } finally {
      setRunningConfigs(prev => {
        const newSet = new Set(prev);
        newSet.delete(browserConfig.id);
        return newSet;
      });
    }
  };

  const handleReplayConfiguration = async (browserConfig: BrowserConfig) => {
    if (!testCase) return;
    
    setExecutionError(null);
    setReplayingConfigs(prev => new Set(prev).add(browserConfig.id));

    try {
      const result = await TestCaseService.replayTestConfiguration(testCase.id, browserConfig.id);
      
      if (onTestStarted && result?.id) {
        onTestStarted(result.id);
      }
      
      // Close modal and redirect to test run page
      onClose();
      setRunningConfigs(new Set());
      setReplayingConfigs(new Set());
      
      // Navigate to the test run detail page
      if (result?.id) {
        navigate(`/runs/${result.id}`);
      }
    } catch (error: any) {
      console.error('Failed to replay test configuration:', error);
      setExecutionError(error.message || 'Failed to start test replay');
    } finally {
      setReplayingConfigs(prev => {
        const newSet = new Set(prev);
        newSet.delete(browserConfig.id);
        return newSet;
      });
    }
  };

  const getBrowserDisplayInfo = (config: BrowserConfig) => {
    const channel = config.browserChannel || 'Default';
    const viewport = `${config.viewport.width}x${config.viewport.height}`;
    const userAgent = config.userAgent ? config.userAgent.slice(0, 60) + '...' : 'Default';
    
    return { channel, viewport, userAgent };
  };

  // Check replay availability for each config when modal opens
  React.useEffect(() => {
    if (isOpen && testCase) {
      const checkReplayAvailability = async () => {
        const availability: Record<string, boolean> = {};
        for (const config of testCase.browserConfigs || []) {
          availability[config.id] = await TestCaseService.hasSuccessfulRuns(testCase.id, config.id);
        }
        setReplayAvailability(availability);
      };
      checkReplayAvailability();
    }
  }, [isOpen, testCase]);

  if (!isOpen) return null;

  const availableConfigs = testCase?.browserConfigs || [];

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
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-[10001] p-4">
        <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[80vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
                <Play className="w-5 h-5 text-indigo-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Run Test</h2>
                <p className="text-sm text-gray-500">Select a browser configuration to execute</p>
              </div>
            </div>
                          <button
                onClick={onClose}
                disabled={runningConfigs.size > 0 || replayingConfigs.size > 0}
                className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
              <X className="w-4 h-4 text-gray-500" />
            </button>
          </div>
          
          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[60vh]">
            {executionError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-700">{executionError}</p>
              </div>
            )}

            {availableConfigs.length === 0 ? (
              <div className="text-center py-8">
                <Monitor className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No Browser Configurations</h3>
                <p className="text-gray-500">
                  You need to add browser configurations before running tests.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-gray-700 mb-3">
                  Browser Configurations ({availableConfigs.length})
                </h3>
                
                {availableConfigs.map((config) => {
                  const { channel, viewport, userAgent } = getBrowserDisplayInfo(config);
                  const isRunning = runningConfigs.has(config.id);
                  const isReplaying = replayingConfigs.has(config.id);
                  const canReplay = replayAvailability[config.id] === true;
                  const isAnyRunning = runningConfigs.size > 0 || replayingConfigs.size > 0;
                  
                  return (
                    <div
                      key={config.id}
                      className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center">
                          <Monitor className="w-4 h-4 text-gray-600" />
                        </div>
                        <div className="flex-1">
                          <h4 className="font-medium text-gray-900 mb-1">{channel}</h4>
                          <div className="text-xs text-gray-500 space-y-1">
                            <div className="flex items-center space-x-4">
                              <span>{viewport}</span>
                              {config.geolocation && (
                                <>
                                  <span>•</span>
                                  <span>Location: {config.geolocation.latitude}, {config.geolocation.longitude}</span>
                                </>
                              )}
                            </div>
                            <div>UA: {userAgent}</div>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        {/* Run with AI Button */}
                        <button
                          onClick={() => handleRunConfiguration(config)}
                          disabled={isAnyRunning}
                          className={`inline-flex items-center px-4 py-2 text-sm font-medium border border-transparent rounded-lg focus:ring-2 focus:ring-offset-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap ${
                            isRunning 
                              ? 'bg-gray-100 text-gray-500' 
                              : 'bg-indigo-600 hover:bg-indigo-700 text-white focus:ring-indigo-500'
                          }`}
                        >
                          {isRunning ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Starting...
                            </>
                          ) : (
                            <>
                              <Play className="w-4 h-4 mr-2" />
                              Run with AI
                            </>
                          )}
                        </button>

                        {/* Replay Button */}
                        <button
                          onClick={() => handleReplayConfiguration(config)}
                          disabled={!canReplay || isAnyRunning}
                          className={`inline-flex items-center px-4 py-2 text-sm font-medium border rounded-lg focus:ring-2 focus:ring-offset-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap ${
                            isReplaying
                              ? 'bg-gray-100 text-gray-500 border-gray-200'
                              : canReplay
                              ? 'bg-green-600 hover:bg-green-700 text-white border-transparent focus:ring-green-500'
                              : 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed'
                          }`}
                          title={!canReplay ? 'No successful runs available for replay' : 'Replay previous successful run'}
                        >
                          {isReplaying ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Replaying...
                            </>
                          ) : (
                            <>
                              <RotateCcw className="w-4 h-4 mr-2" />
                              Replay
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
          
          {/* Footer */}
          {availableConfigs.length > 0 && (
            <div className="flex items-center justify-between p-6 pt-0">
              <div className="text-sm text-gray-500">
                {(runningConfigs.size > 0 || replayingConfigs.size > 0) && (
                  <span>
                    {runningConfigs.size > 0 && 'Starting AI test execution...'}
                    {replayingConfigs.size > 0 && 'Starting replay...'}
                  </span>
                )}
              </div>
              <button
                disabled
                className="px-4 py-2 text-sm font-medium text-gray-400 bg-gray-100 border border-gray-200 rounded-lg cursor-not-allowed"
              >
                Run all (coming soon)
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
};
