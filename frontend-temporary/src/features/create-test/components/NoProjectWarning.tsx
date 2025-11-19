import React from 'react';
import { AlertCircle } from 'lucide-react';

export const NoProjectWarning: React.FC = () => {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-800">Create Test Case</h1>
        <p className="mt-1 text-gray-600">Create a new automated test case for your application</p>
      </div>
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-6">
        <div className="flex items-center">
          <AlertCircle className="w-5 h-5 text-amber-600 mr-3" />
          <div>
            <h3 className="text-sm font-semibold text-amber-800">No Project Selected</h3>
            <p className="text-sm text-amber-700 mt-1">Please select a project from the sidebar to create test cases.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
