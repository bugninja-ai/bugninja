import React from 'react';
import { Lock, ZoomIn, Image, Brain } from 'lucide-react';
import { getStatusColor, getStatusIcon, getActionIcon, formatDuration } from './TestRunUtils';
import { BASE_DOMAIN } from '../../../shared/services/api';

interface ActionStepProps {
  step: any;
  onScreenshotClick: (screenshot: string, actionData: any) => void;
  runType?: string;
}

export const ActionStep: React.FC<ActionStepProps> = ({ step, onScreenshotClick, runType }) => {
  const isReplayRun = runType === 'REPLAY';
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between p-4 bg-gray-50">
        <div className="flex items-center space-x-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-white border border-gray-200 text-sm font-medium text-gray-700">
            {step.stepNumber}
          </div>
          <h3 className="font-medium text-gray-800">{step.description}</h3>
          <span className={`inline-flex items-center space-x-1 text-xs font-semibold px-2.5 py-1 rounded-full border ${getStatusColor(step.status)}`}>
            {getStatusIcon(step.status)}
            <span>{step.status.charAt(0).toUpperCase() + step.status.slice(1)}</span>
          </span>
        </div>
        
        <div className="text-sm text-gray-600">
          Duration: {formatDuration(step.duration)}
        </div>
      </div>
      
      <div className="p-4 space-y-4">
        {/* Brain State with Multiple Actions */}
        {step.brainState && (
          <>
            {/* Brain State Section (Purple) - Only show AI reasoning for non-replay runs */}
            {!isReplayRun && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg overflow-hidden mb-4">
                <div className="flex items-center justify-between p-3 bg-purple-100/50">
                  <div className="flex items-center space-x-2">
                    <Brain className="h-4 w-4 text-purple-600" />
                    <span className="text-sm font-semibold text-gray-800">AI brain state</span>
                  </div>
                </div>
                
                <div className="p-4 space-y-3">
                  <div>
                    <p className="text-xs font-medium text-purple-700 mb-1">Evaluate previous goal:</p>
                    <div className="text-sm text-purple-800 bg-white/70 border border-purple-200 rounded p-2">
                      {step.brainState.actions[0]?.evaluatePreviousGoal || 'No evaluation available'}
                    </div>
                  </div>
                  
                  <div>
                    <p className="text-xs font-medium text-purple-700 mb-1">Next goal:</p>
                    <div className="text-sm text-purple-800 bg-white/70 border border-purple-200 rounded p-2">
                      {step.brainState.actions[0]?.nextGoal || 'No next goal available'}
                    </div>
                  </div>
                  
                  <div>
                    <p className="text-xs font-medium text-purple-700 mb-1">Memory:</p>
                    <div className="text-sm text-purple-800 bg-white/70 border border-purple-200 rounded p-2">
                      {step.brainState.actions[0]?.memory || 'No memory available'}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Actions Section (Light Blue) - Show actions for all run types */}
            <div className="space-y-3 mb-4">
              <div className="text-sm font-medium text-gray-700 mb-2">
                {isReplayRun ? 'Replay actions taken:' : 'Actions taken:'}
              </div>
              {step.brainState.actions.map((action: any) => (
                <div key={action.id} className="bg-indigo-50 border border-indigo-200 rounded-lg overflow-hidden">
                  <div className="flex items-center justify-between p-3 bg-indigo-100/50">
                    <div className="flex items-center space-x-2">
                      {getActionIcon(action.actionType, action.icon)}
                      <span className="text-sm font-medium text-indigo-800">
                        {action.actionType}
                      </span>
                    </div>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                      action.status === 'passed' 
                        ? 'text-green-600 bg-green-50 border-green-200' 
                        : 'text-red-600 bg-red-50 border-red-200'
                    }`}>
                      {action.status.toUpperCase()}
                    </span>
                  </div>
                  
                  <div className="p-3">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                      <div className="lg:col-span-2">
                        <div className="space-y-2 text-sm">
                          {action.url && (
                            <div className="flex items-center space-x-2">
                              <span className="text-xs font-medium text-indigo-700 min-w-16">URL:</span>
                              <span className="text-xs text-indigo-800 bg-white/70 px-2 py-1 rounded break-all font-mono">
                                {action.url}
                              </span>
                            </div>
                          )}
                          
                          {action.xpath && action.xpath !== 'N/A' && (
                            <div className="flex items-center space-x-2">
                              <span className="text-xs font-medium text-indigo-700 min-w-16">XPath:</span>
                              <span className="text-xs text-indigo-600 bg-indigo-100 px-2 py-1 rounded font-mono break-all">
                                {action.xpath}
                              </span>
                            </div>
                          )}
                          
                          {action.inputText && (
                            <div className="flex items-center space-x-2">
                              <span className="text-xs font-medium text-indigo-700 min-w-16">Input:</span>
                              <span className="text-xs text-indigo-800 bg-white/70 px-2 py-1 rounded flex items-center space-x-1">
                                {action.isSecret && <Lock className="w-3 h-3" />}
                                <span>{action.inputText}</span>
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex justify-center lg:justify-end">
                        {action.screenshot && action.screenshot !== 'No screenshot' ? (
                          <div 
                            className="w-48 h-32 bg-gray-100 border-2 border-gray-300 rounded-lg overflow-hidden cursor-pointer group hover:border-indigo-400 transition-all duration-200 relative"
                            onClick={() => onScreenshotClick(action.screenshot, action)}
                          >
                            <img
                              src={`${BASE_DOMAIN}/${action.screenshot}`}
                              alt="Action screenshot"
                              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                            />
                            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-200 flex items-center justify-center">
                              <ZoomIn className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
                            </div>
                          </div>
                        ) : (
                          <div className="w-48 h-32 bg-gray-100 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center">
                            <div className="text-center">
                              <Image className="h-6 w-6 text-gray-400 mx-auto mb-1" />
                              <p className="text-xs text-gray-500">No screenshot</p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Regular Step Content (Expected/Actual for non-brain state steps) */}
        {!step.brainState && (
          <>
            {step.expected && (
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">Expected:</p>
                <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                  <p className="text-sm text-blue-800">{step.expected}</p>
                </div>
              </div>
            )}
            
            {step.actual && (
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">Actual:</p>
                <div className={`border rounded-md p-3 ${
                  step.status === 'passed' 
                    ? 'bg-green-50 border-green-200' 
                    : step.status === 'failed'
                    ? 'bg-red-50 border-red-200'
                    : 'bg-gray-50 border-gray-200'
                }`}>
                  <p className={`text-sm ${
                    step.status === 'passed' 
                      ? 'text-green-800' 
                      : step.status === 'failed'
                      ? 'text-red-800'
                      : 'text-gray-800'
                  }`}>
                    {step.actual}
                  </p>
                </div>
              </div>
            )}
            
            {step.screenshot && (
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">Screenshot:</p>
                <div 
                  className="bg-gray-100 border border-gray-200 rounded-lg overflow-hidden cursor-pointer group hover:border-indigo-400 transition-all duration-200 relative h-48 w-full max-w-md"
                  onClick={() => onScreenshotClick(step.screenshot, { 
                    actionType: step.description,
                    status: step.status as 'passed' | 'failed'
                  })}
                >
                  <img
                    src={`${BASE_DOMAIN}/${step.screenshot}`}
                    alt="Step screenshot"
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                  />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-200 flex items-center justify-center">
                    <ZoomIn className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        
        {/* Error Details */}
        {step.error && (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Error details:</p>
            <div className="bg-red-50 border border-red-200 rounded-md p-3">
              <p className="text-sm text-red-800">{step.error}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
