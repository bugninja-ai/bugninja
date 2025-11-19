import React from 'react';
import { MonitorPlay } from 'lucide-react';
import { BASE_DOMAIN } from '../../../shared/services/api';

interface TestRunGifProps {
  gif: string;
}

export const TestRunGif: React.FC<TestRunGifProps> = ({ gif }) => {
  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200 mb-6">
      <div className="flex items-center space-x-2 mb-4">
        <MonitorPlay className="h-5 w-5 text-indigo-600" />
        <span className="text-lg font-semibold text-gray-800">Test execution recording</span>
      </div>
      <div className="flex justify-center">
        <div className="bg-gray-100 border border-gray-200 rounded-lg overflow-hidden max-w-4xl w-full">
          <img
            src={`${BASE_DOMAIN}/${gif}`}
            alt="Test execution recording"
            className="w-full h-auto"
            style={{ maxHeight: '600px', objectFit: 'contain' }}
          />
        </div>
      </div>
    </div>
  );
};
