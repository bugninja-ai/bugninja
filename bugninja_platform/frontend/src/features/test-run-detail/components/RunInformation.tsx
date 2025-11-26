import React from 'react';
import { Calendar, Timer, CheckCircle, XCircle } from 'lucide-react';
import { TestRun } from '../../test-runs/types';
import { formatDate, formatDuration } from './TestRunUtils';

interface RunInformationProps {
  testRun: TestRun;
}

export const RunInformation: React.FC<RunInformationProps> = ({ testRun }) => {
  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Run information</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div>
          <div className="flex items-center space-x-2 mb-2">
            <Calendar className="h-4 w-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-700">Last run</span>
          </div>
          <p className="text-gray-800">{formatDate(testRun.startedAt)}</p>
        </div>

        <div>
          <div className="flex items-center space-x-2 mb-2">
            <Timer className="h-4 w-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-700">Duration</span>
          </div>
          <p className="text-gray-800">{formatDuration(testRun.duration)}</p>
        </div>

        <div>
          <div className="flex items-center space-x-2 mb-2">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <span className="text-sm font-medium text-gray-700">Passed steps</span>
          </div>
          <p className="text-green-600 font-semibold">{testRun.passedSteps}/{testRun.totalSteps}</p>
        </div>

        <div>
          <div className="flex items-center space-x-2 mb-2">
            <XCircle className="h-4 w-4 text-red-600" />
            <span className="text-sm font-medium text-gray-700">Failed steps</span>
          </div>
          <p className="text-red-600 font-semibold">{testRun.failedSteps}/{testRun.totalSteps}</p>
        </div>
      </div>
    </div>
  );
};
