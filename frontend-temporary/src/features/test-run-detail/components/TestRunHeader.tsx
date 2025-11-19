import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, FileText } from 'lucide-react';
import { TestRun } from '../../test-runs/types';
import { getStatusColor, getStatusIcon } from './TestRunUtils';

interface TestRunHeaderProps {
  testRun: TestRun;
}

export const TestRunHeader: React.FC<TestRunHeaderProps> = ({ testRun }) => {
  return (
    <div className="flex items-start justify-between">
      <div className="flex-1">
        <div className="flex items-center space-x-2 mb-2">
          <h1 className="text-3xl font-bold text-gray-800">{testRun.testCase.title}</h1>
          <span className={`inline-flex items-center space-x-1 text-xs font-semibold px-2.5 py-1 rounded-full border ${getStatusColor(testRun.status)}`}>
            {getStatusIcon(testRun.status)}
            <span>{testRun.status.toUpperCase()}</span>
          </span>
          <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded-lg">{testRun.id || 'N/A'}</span>
        </div>
        <p className="text-gray-600 mb-4">{testRun.testCase.description}</p>
      </div>

      <div className="flex items-center space-x-3">
        <Link
          to="/runs"
          className="inline-flex items-center px-3 py-2 text-sm font-medium border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to test runs
        </Link>
        
        <Link
          to={`/test-details/${testRun.testCase.id}`}
          className="inline-flex items-center px-3 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
        >
          <FileText className="w-4 h-4 mr-1" />
          View test case
        </Link>
      </div>
    </div>
  );
};
