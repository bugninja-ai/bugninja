import React from 'react';
import { Trash2 } from 'lucide-react';
import { FrontendTestCase } from '../types';

interface DeleteTestCaseSectionProps {
  testCase: FrontendTestCase;
  onDelete: () => void;
}

export const DeleteTestCaseSection: React.FC<DeleteTestCaseSectionProps> = ({
  onDelete
}) => {
  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-red-200">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-red-800 mb-2">Danger Zone</h2>
          <p className="text-gray-600">Permanently delete this test case and all associated data.</p>
        </div>
        <button
          onClick={onDelete}
          className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
        >
          <Trash2 className="w-4 h-4 mr-2" />
          Delete Test Case
        </button>
      </div>
    </div>
  );
};
