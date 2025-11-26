import React from 'react';
import { FrontendTestCase } from '../types';

interface ExecutionSummaryProps {
  testCase: FrontendTestCase;
}

export const ExecutionSummary: React.FC<ExecutionSummaryProps> = ({ testCase }) => {
  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Execution summary</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-800">{testCase.totalRuns}</div>
          <div className="text-sm text-gray-600">Total Runs</div>
        </div>
        
        <div className="text-center">
          <div className="text-2xl font-bold text-emerald-600">{testCase.passedRuns}</div>
          <div className="text-sm text-gray-600">Passed</div>
        </div>
        
        <div className="text-center">
          <div className="text-2xl font-bold text-red-600">{testCase.failedRuns}</div>
          <div className="text-sm text-gray-600">Failed</div>
        </div>
      </div>
      
      <div className="mt-4 bg-gray-200 rounded-full h-2">
        <div 
          className="bg-emerald-500 h-2 rounded-full transition-all duration-300"
          style={{ width: `${testCase.passRate}%` }}
        ></div>
      </div>
      <div className="text-center mt-2 text-sm text-gray-600">
        {testCase.passRate}% success rate
      </div>
    </div>
  );
};
