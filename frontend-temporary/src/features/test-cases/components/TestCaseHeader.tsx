import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Play } from 'lucide-react';
import { FrontendTestCase } from '../types';
import { StatusBadge } from '../../../shared/components/StatusBadge';
import { PriorityBadge } from '../../../shared/components/PriorityBadge';

interface TestCaseHeaderProps {
  testCase: FrontendTestCase;
  onRunTest?: () => void;
}

export const TestCaseHeader: React.FC<TestCaseHeaderProps> = ({ testCase, onRunTest }) => {
  return (
    <div className="flex items-start justify-between">
      <div className="flex-1">
        <div className="flex items-center space-x-3 mb-2">
          <h1 className="text-3xl font-bold text-gray-800">{testCase.title}</h1>
          <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded-lg">
            {testCase.code}
          </span>
          <PriorityBadge priority={testCase.priority} />
          <StatusBadge status={testCase.status} />
        </div>
        <p className="text-gray-600 mb-4">{testCase.description}</p>
      </div>

      <div className="flex items-center space-x-3">
        {onRunTest && (
          <button
            onClick={onRunTest}
            className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
          >
            <Play className="h-4 w-4 mr-2" />
            Run Test
          </button>
        )}
        <Link
          to="/"
          className="inline-flex items-center px-3 py-2 text-sm font-medium border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to test cases
        </Link>
      </div>
    </div>
  );
};
