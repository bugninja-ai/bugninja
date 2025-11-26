import React from 'react';
import { CheckCircle } from 'lucide-react';

export const SuccessModal: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="bg-white/80 backdrop-blur-sm rounded-lg p-8 border border-gray-200 text-center max-w-md mx-auto">
        <div className="w-16 h-16 bg-emerald-100 rounded-lg flex items-center justify-center mx-auto mb-4">
          <CheckCircle className="w-8 h-8 text-emerald-600" />
        </div>
        <h3 className="text-xl font-semibold text-gray-800 mb-2">Test Case Created!</h3>
        <p className="text-gray-600">Your test case has been successfully created and is ready to run.</p>
      </div>
    </div>
  );
};
