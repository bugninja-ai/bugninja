import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorFallbackProps {
  resetErrorBoundary: () => void;
}

export const ErrorFallback: React.FC<ErrorFallbackProps> = ({ 
  resetErrorBoundary 
}) => {
  return (
    <div className="min-h-[400px] flex items-center justify-center p-8">
      <div className="text-center max-w-md">
        <div className="mb-4">
          <AlertTriangle className="w-16 h-16 text-red-500 mx-auto" />
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Something went wrong
        </h2>
        <p className="text-gray-600 mb-6">
          An unexpected error occurred. This has been logged for investigation.
        </p>
        <div className="space-y-3">
          <button
            onClick={resetErrorBoundary}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Try Again
          </button>
          <div>
            <button
              onClick={() => window.location.reload()}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Reload Page
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
