import React from 'react';
import { Link } from 'react-router-dom';
import { 
  History, 
  Loader2, 
  Clock, 
  Calendar, 
  Eye, 
  PlaySquare, 
  User, 
  Computer, 
  Monitor, 
  Play 
} from 'lucide-react';
import { FrontendTestCase } from '../types';
import { StatusBadge } from '../../../shared/components/StatusBadge';
import { BASE_DOMAIN } from '../../../shared/services/api';

interface RecentTestRunsProps {
  testCase: FrontendTestCase;
  recentTestRuns: any[];
  testRunsLoading: boolean;
  onRunTest?: () => void;
}

export const RecentTestRuns: React.FC<RecentTestRunsProps> = ({
  testCase,
  recentTestRuns,
  testRunsLoading,
  onRunTest
}) => {
  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800">Recent test runs</h2>
        <Link
          to={`/runs?testCase=${testCase.id}`}
          className="inline-flex items-center px-3 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
        >
          <History className="w-4 h-4 mr-1" />
          View all runs
        </Link>
      </div>
      
      <div className="space-y-4">
        {testRunsLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-indigo-600 mr-2" />
            <span className="text-gray-600">Loading recent test runs...</span>
          </div>
        ) : recentTestRuns.length > 0 ? (
          recentTestRuns.map((run) => {
            const startedAt = new Date(run.started_at || run.startedAt || run.created_at);
            const completedAt = run.finished_at || run.completed_at || run.completedAt;
            const duration = run.duration || (completedAt ? (new Date(completedAt).getTime() - startedAt.getTime()) / 1000 : 0);
            const passedSteps = run.passed_steps || run.passedSteps || 0;
            const totalSteps = run.total_steps || run.totalSteps || run.steps?.length || 0;
            const status = (run.status || run.current_state || 'PENDING').toUpperCase();
            const runGifPath = run.run_gif || run.runGif;
            const runGif = runGifPath ? `${BASE_DOMAIN}/${runGifPath}` : null;
            const runType = run.run_type || run.runType;
            const origin = run.origin;
            const browserConfig = run.browser_config || run.browserConfig;
            
            return (
              <div key={run.id} className="relative group bg-white rounded-lg p-6 border border-gray-200">
                <div className="flex items-start space-x-4">
                  {/* GIF Display */}
                  {runGif && (
                    <div className="flex-shrink-0">
                      <div className="relative overflow-hidden rounded-xl border-2 border-gray-200 group-hover:border-gray-300 transition-colors">
                        <img 
                          src={runGif} 
                          alt="Test run animation"
                          className="w-28 h-20 object-cover"
                          onError={(e) => {
                            e.currentTarget.style.display = 'none';
                          }}
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                      </div>
                    </div>
                  )}
                  
                  <div className="flex-1 min-w-0">
                    {/* Header with Status Badge */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center space-x-3">
                        <StatusBadge status={status.toLowerCase()} />
                        
                        {totalSteps > 0 && (
                          <div className="flex items-center space-x-1 text-sm text-gray-600 bg-gray-50 px-2 py-1 rounded-lg">
                            <span className="font-medium">{passedSteps}</span>
                            <span className="text-gray-400">/</span>
                            <span>{totalSteps}</span>
                            <span className="text-xs text-gray-500 ml-1">steps</span>
                          </div>
                        )}
                      </div>
                      
                      <Link
                        to={`/runs/${run.id}`}
                        className="inline-flex items-center px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-all duration-200"
                      >
                        <Eye className="w-4 h-4 mr-1.5" />
                        View details
                      </Link>
                    </div>
                    
                    {/* Details Row */}
                    <div className="flex items-center flex-wrap gap-x-6 gap-y-2">
                      <div className="flex items-center space-x-2 text-sm">
                        <Calendar className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-600">{startedAt.toLocaleDateString()} {startedAt.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                      </div>
                      
                      {duration > 0 && (
                        <div className="flex items-center space-x-2 text-sm">
                          <Clock className="w-4 h-4 text-gray-400" />
                          <span className="text-gray-600">{duration.toFixed(1)}s</span>
                        </div>
                      )}

                      {runType && (
                        <div className="flex items-center space-x-1.5 text-sm">
                          <PlaySquare className="w-4 h-4 text-gray-400" />
                          <span className="text-gray-600">{runType}</span>
                        </div>
                      )}
                      
                      {origin && (
                        <div className="flex items-center space-x-1.5 text-sm">
                          {origin.toLowerCase().includes('user') ? (
                            <User className="w-4 h-4 text-gray-400" />
                          ) : (
                            <Computer className="w-4 h-4 text-gray-400" />
                          )}
                          <span className="text-gray-600">{origin}</span>
                        </div>
                      )}
                      
                      {browserConfig?.browser_config?.viewport && (
                        <div className="flex items-center space-x-1.5 text-sm">
                          <Monitor className="w-4 h-4 text-gray-400" />
                          <span className="text-gray-600">{browserConfig.browser_config.viewport.width}×{browserConfig.browser_config.viewport.height}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <Clock className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-800 mb-2">No test runs yet</h3>
            <p className="text-gray-600 mb-4">This test case hasn't been executed yet.</p>
            {onRunTest ? (
              <button
                onClick={onRunTest}
                className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
              >
                <Play className="w-4 h-4 mr-2" />
                Run test now
              </button>
            ) : (
              <Link
                to={`/runs/${testCase.id}/run`}
                className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
              >
                <Play className="w-4 h-4 mr-2" />
                Run test now
              </Link>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
