import React from 'react';
import { Link } from 'react-router-dom';
import { FileText, Calendar, BarChart3 } from 'lucide-react';
import { FrontendTestCase } from '../types';
import { StatusBadge, PriorityBadge } from '../../../shared/components';

interface TestCaseTableViewProps {
  testCases: FrontendTestCase[];
}

export const TestCaseTableView: React.FC<TestCaseTableViewProps> = ({
  testCases,
}) => {
  const formatDate = (date: Date | undefined) => {
    if (!date) return 'Never';
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const capitalizeCategory = (category: string) => {
    return category.charAt(0).toUpperCase() + category.slice(1);
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          {/* Table Header */}
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left py-3 px-4 font-medium text-gray-900 text-sm">
                Test name
              </th>
              <th className="text-left py-3 px-4 font-medium text-gray-900 text-sm">
                Priority
              </th>
              <th className="text-left py-3 px-4 font-medium text-gray-900 text-sm">
                Status
              </th>
              <th className="text-left py-3 px-4 font-medium text-gray-900 text-sm">
                Category
              </th>
              <th className="text-left py-3 px-4 font-medium text-gray-900 text-sm">
                Last run
              </th>
              <th className="text-left py-3 px-4 font-medium text-gray-900 text-sm">
                Total runs
              </th>
              <th className="text-right py-3 px-4 font-medium text-gray-900 text-sm">
                Actions
              </th>
            </tr>
          </thead>

          {/* Table Body */}
          <tbody className="divide-y divide-gray-200">
            {testCases.map((testCase) => (
              <tr 
                key={testCase.id} 
                className="hover:bg-gray-50 transition-colors"
              >
                {/* Test Name */}
                <td className="py-4 px-4">
                  <div className="flex flex-col">
                    <Link
                      to={`/test-details/${testCase.id}`}
                      className="font-medium text-gray-900 hover:text-indigo-600 transition-colors"
                    >
                      {testCase.title}
                    </Link>
                    <span className="text-sm text-gray-500 mt-1">{testCase.code}</span>
                  </div>
                </td>

                {/* Priority */}
                <td className="py-4 px-4">
                  <PriorityBadge priority={testCase.priority} />
                </td>

                {/* Status */}
                <td className="py-4 px-4">
                  <StatusBadge status={testCase.status} />
                </td>

                {/* Category */}
                <td className="py-4 px-4">
                  <span className="inline-flex items-center px-2.5 py-1 rounded-full border text-xs font-semibold bg-gray-100 text-gray-800 border-gray-200">
                    {capitalizeCategory(testCase.category || 'general')}
                  </span>
                </td>

                {/* Last Run */}
                <td className="py-4 px-4">
                  <div className="flex items-center text-sm text-gray-500">
                    <Calendar className="w-4 h-4 mr-1" />
                    <span>{formatDate(testCase.lastRunAt)}</span>
                  </div>
                </td>

                {/* Total Runs */}
                <td className="py-4 px-4">
                  <div className="flex items-center text-sm text-gray-900">
                    <BarChart3 className="w-4 h-4 mr-1 text-gray-400" />
                    {testCase.totalRuns}
                  </div>
                </td>

                {/* Actions */}
                <td className="py-4 px-4 text-right">
                  <Link
                    to={`/test-details/${testCase.id}`}
                    className="inline-flex items-center px-3 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
                  >
                    <FileText className="w-4 h-4 mr-1" />
                    View details
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
