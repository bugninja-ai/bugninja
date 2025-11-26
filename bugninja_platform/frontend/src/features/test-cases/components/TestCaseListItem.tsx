import React from 'react';
import { Link } from 'react-router-dom';
import { 
  Play,
  Calendar,
  Clock,
  FileText
} from 'lucide-react';
import { FrontendTestCase } from '../types';
import { StatusBadge } from '../../../shared/components/StatusBadge';
import { PriorityBadge } from '../../../shared/components/PriorityBadge';

interface TestCaseListItemProps {
  testCase: FrontendTestCase;
}



export const TestCaseListItem: React.FC<TestCaseListItemProps> = ({
  testCase
}) => {
  return (
    <div className="bg-white rounded-lg p-6 border border-gray-200 hover:border-gray-300 transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-2">
            <h3 className="text-lg font-semibold text-gray-800">{testCase.title}</h3>
            <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded-lg">{testCase.code}</span>
            <PriorityBadge priority={testCase.priority} />
            <StatusBadge 
              status={testCase.status} 
 
            />
          </div>
          
          <p className="text-gray-600 mb-4">{testCase.description}</p>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-500">
            <div className="flex items-center space-x-1">
              <Calendar className="w-4 h-4" />
              <span>Created: {testCase.createdAt.toLocaleDateString()}</span>
            </div>
            <div className="flex items-center space-x-1">
              <Clock className="w-4 h-4" />
              <span>Last run: {testCase.lastRunAt ? testCase.lastRunAt.toLocaleDateString() : 'Never'}</span>
            </div>
            <div className="flex items-center space-x-1">
              <span className="text-gray-400">Runs:</span>
              <span className="text-gray-600 font-medium">{testCase.totalRuns}</span>
            </div>
            <div className="flex items-center space-x-1">
              <span className="text-gray-400">Category:</span>
              <span className="text-gray-600 font-medium">{testCase.category.charAt(0).toUpperCase() + testCase.category.slice(1)}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2 ml-4">
          <Link
            to={`/test-details/${testCase.id}`}
            className="inline-flex items-center px-3 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
          >
            <FileText className="w-4 h-4 mr-1" />
            View details
          </Link>
          
          <Link
            to={`/runs/${testCase.id}`}
            className="inline-flex items-center px-3 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
          >
            <Play className="w-4 h-4 mr-1" />
            Run test
          </Link>
        </div>
      </div>
    </div>
  );
};
