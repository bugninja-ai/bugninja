import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface ErrorSectionProps {
  error: string;
}

export const ErrorSection: React.FC<ErrorSectionProps> = ({ error }) => {
  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200">
      <div className="flex items-start space-x-3">
        <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
        <div>
          <h3 className="text-sm font-medium text-red-800">Test run error</h3>
          <p className="text-sm text-red-700 mt-1">{error}</p>
        </div>
      </div>
    </div>
  );
};
