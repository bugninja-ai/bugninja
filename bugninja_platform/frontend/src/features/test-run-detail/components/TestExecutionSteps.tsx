import React from 'react';
import { Clock } from 'lucide-react';
import { TestRun } from '../../test-runs/types';
import { ActionStep } from './ActionStep';

interface TestExecutionStepsProps {
  testRun: TestRun;
  onScreenshotClick: (screenshot: string, actionData: any) => void;
}

export const TestExecutionSteps: React.FC<TestExecutionStepsProps> = ({ 
  testRun, 
  onScreenshotClick 
}) => {
  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200">
      <h2 className="text-lg font-semibold text-gray-800 mb-6">Test execution steps</h2>
      
      <div className="space-y-6">
        {testRun.steps.map((step) => (
          <ActionStep
            key={step.id}
            step={step}
            onScreenshotClick={onScreenshotClick}
            runType={testRun.runType}
          />
        ))}
      </div>
      
      {testRun.steps.length === 0 && (
        <div className="text-center py-8">
          <Clock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-800 mb-2">No execution steps</h3>
          <p className="text-gray-600">This test run hasn't been executed yet or has no recorded steps.</p>
        </div>
      )}
    </div>
  );
};
