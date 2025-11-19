import React from 'react';
import { Upload, FileText } from 'lucide-react';

interface MethodSelectionProps {
  method: 'upload' | 'manual';
  onMethodChange: (method: 'upload' | 'manual') => void;
}

export const MethodSelection: React.FC<MethodSelectionProps> = ({
  method,
  onMethodChange
}) => {
  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200 relative z-0">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Choose Creation Method</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button
          type="button"
          onClick={() => onMethodChange('manual')}
          className={`p-6 rounded-lg border-2 transition-colors ${
            method === 'manual'
              ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
              : 'border-gray-200 bg-white hover:border-gray-300 text-gray-700'
          }`}
        >
          <FileText className="w-8 h-8 mx-auto mb-3" />
          <h3 className="font-semibold mb-2">Manual Entry</h3>
          <p className="text-sm">Create test case by filling out the form manually</p>
        </button>
        
        <button
          type="button"
          onClick={() => onMethodChange('upload')}
          className={`p-6 rounded-lg border-2 transition-colors ${
            method === 'upload'
              ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
              : 'border-gray-200 bg-white hover:border-gray-300 text-gray-700'
          }`}
        >
          <Upload className="w-8 h-8 mx-auto mb-3" />
          <h3 className="font-semibold mb-2">File Upload</h3>
          <p className="text-sm">Upload a test case file (.csv, .json, .txt, .doc, .docx, .pdf, .xlsx)</p>
        </button>
      </div>
    </div>
  );
};
