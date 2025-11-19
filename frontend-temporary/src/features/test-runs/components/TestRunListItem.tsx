import React from 'react';
import { Link } from 'react-router-dom';
import { 
  Calendar,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Eye,
  Monitor
} from 'lucide-react';

interface TestRunListItemProps {
  run: any; // TODO: Create proper TestRun type
}

const getStatusIcon = (status: string) => {
  switch (status.toLowerCase()) {
    case 'finished':
      return <CheckCircle className="w-4 h-4 text-emerald-500" />;
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-500" />;
    case 'pending':
      return <Clock className="w-4 h-4 text-amber-500" />;
    default:
      return <AlertCircle className="w-4 h-4 text-amber-500" />;
  }
};

const getStatusColor = (status: string) => {
  switch (status.toLowerCase()) {
    case 'finished':
      return 'bg-emerald-100 text-emerald-800 border-emerald-200';
    case 'failed':
      return 'bg-red-100 text-red-800 border-red-200';
    case 'pending':
      return 'bg-amber-100 text-amber-800 border-amber-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
};

const formatDuration = (seconds: number) => {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  } else {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  }
};

const getBrowserInfo = (run: any) => {
  // Extract browser info from browser_config
  const browserConfig = run.browser_config?.browser_config;
  const userAgent = browserConfig?.user_agent || '';
  const viewport = browserConfig?.viewport || { width: 0, height: 0 };
  
  // Determine browser name from user agent
  let browserName = 'Unknown Browser';
  if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) {
    browserName = 'Safari';
  } else if (userAgent.includes('Chrome')) {
    browserName = 'Chrome';
  } else if (userAgent.includes('Firefox')) {
    browserName = 'Firefox';
  } else if (userAgent.includes('Edge')) {
    browserName = 'Edge';
  }
  
  const resolution = viewport.width > 0 && viewport.height > 0 
    ? `${viewport.width}x${viewport.height}` 
    : 'Unknown resolution';
  
  return {
    name: browserName,
    resolution: resolution
  };
};

const getRunTypeDisplay = (runType: string) => {
  switch (runType) {
    case 'AGENTIC':
      return 'Agentic';
    case 'REPLAY':
      return 'Replay';
    case 'REPLAY_WITH_HEALING':
      return 'Healing';
    default:
      return 'Agentic';
  }
};

export const TestRunListItem: React.FC<TestRunListItemProps> = ({ run }) => {
  const browserInfo = getBrowserInfo(run);
  const startedAt = new Date(run.started_at || run.startedAt || run.created_at);
  
  // Calculate duration from start/finish times if available
  let duration = run.duration || 0;
  if (run.finished_at && run.started_at && duration === 0) {
    duration = (new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 1000;
  }
  
  const passedSteps = run.passed_steps || run.passedSteps || 0;
  const failedSteps = run.failed_steps || run.failedSteps || 0;
  const totalSteps = run.total_steps || run.totalSteps || passedSteps + failedSteps;
  
  // Map backend status to frontend status
  const statusMap: { [key: string]: string } = {
    'PASSED': 'finished',
    'FAILED': 'failed',
    'PENDING': 'pending',
    'RUNNING': 'pending',
    'FINISHED': 'finished',
    'ERROR': 'failed'
  };
  const mappedStatus = statusMap[run.current_state] || 'pending';

  return (
    <div className="bg-white rounded-lg p-6 border border-gray-200 hover:border-gray-300 transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-2">
            <h3 className="text-lg font-semibold text-gray-800">
              {run.test_case?.test_name || run.testCase?.title || `Test Run - ${run.id?.slice(-8)}`}
            </h3>
            <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded-lg">
              {run.id || 'N/A'}
            </span>
            <span className={`inline-flex items-center space-x-1 text-xs font-semibold px-2.5 py-1 rounded-full border ${getStatusColor(mappedStatus)}`}>
              {getStatusIcon(mappedStatus)}
              <span>{mappedStatus?.charAt(0).toUpperCase() + mappedStatus?.slice(1)}</span>
            </span>
          </div>
          
          <p className="text-gray-600 mb-3">
            {run.test_case?.test_description || run.testCase?.description || 'No description available'}
          </p>

          {/* Browser and Resolution Info */}
          <div className="flex items-center space-x-4 mb-4 text-sm text-gray-600">
            <div className="flex items-center space-x-1">
              <Monitor className="w-4 h-4 text-gray-400" />
              <span>{browserInfo.name}</span>
            </div>
            <div className="flex items-center space-x-1">
              <span className="text-gray-400">•</span>
              <span>{browserInfo.resolution}</span>
            </div>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-500">
            <div className="flex items-center space-x-1">
              <Calendar className="w-4 h-4" />
              <span>Started: {startedAt.toLocaleDateString()}</span>
            </div>
            <div className="flex items-center space-x-1">
              <Clock className="w-4 h-4" />
              <span>Duration: {formatDuration(duration)}</span>
            </div>
            {totalSteps > 0 && (
              <div className="flex items-center space-x-1">
                <span className="text-gray-400">Steps:</span>
                <span className="text-emerald-600 font-medium">{passedSteps}</span>
                <span className="text-gray-400">/</span>
                <span className="text-red-600 font-medium">{failedSteps}</span>
                <span className="text-gray-400">/</span>
                <span className="font-medium">{totalSteps}</span>
              </div>
            )}
            <div className="flex items-center space-x-1">
              <span className="text-gray-400">Type:</span>
              <span className="text-gray-600 font-medium">{getRunTypeDisplay(run.run_type)}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3 ml-4">
          <Link
            to={`/runs/${run.id}`}
            className="inline-flex items-center px-3 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
          >
            <Eye className="w-4 h-4 mr-1" />
            View details
          </Link>
        </div>
      </div>
    </div>
  );
};
