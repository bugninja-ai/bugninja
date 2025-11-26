import React from 'react';
import { Target } from 'lucide-react';

interface TestGoalSectionProps {
  goal: string;
}

export const TestGoalSection: React.FC<TestGoalSectionProps> = ({ goal }) => {
  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200 mt-8 mb-6">
      <div className="flex items-center space-x-2 mb-4">
        <Target className="h-5 w-5 text-blue-600" />
        <span className="text-lg font-semibold text-gray-800">Test goal</span>
      </div>
      <p className="text-gray-600">{goal}</p>
    </div>
  );
};
