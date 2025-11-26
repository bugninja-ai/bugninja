import React from 'react';
import { Upload, X, Loader2, FileText } from 'lucide-react';

interface FileUploadSectionProps {
  file: File | null;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onFileRemove: () => void;
  onProcessFile: () => Promise<void>;
  fileProcessing: boolean;
  fileProcessed: boolean;
}

export const FileUploadSection: React.FC<FileUploadSectionProps> = ({
  file,
  onFileChange,
  onFileRemove,
  onProcessFile,
  fileProcessing,
  fileProcessed
}) => {
  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200 relative z-0">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Upload Test Case File</h2>
      
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-indigo-400 transition-colors">
        <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-800 mb-2">Upload your test case file</h3>
        <p className="text-gray-600 mb-4">Drag and drop your file here, or click to select</p>
        
        <input
          type="file"
          accept=".csv,.json,.txt,.doc,.docx,.pdf,.xlsx,.xls,.py,.js,.ts,.toml,.md"
          onChange={onFileChange}
          className="hidden"
          id="file-upload"
        />
        <label
          htmlFor="file-upload"
          className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors cursor-pointer"
        >
          Select File
        </label>
        
        {file && (
          <div className="mt-4 space-y-3">
            <div className="p-3 bg-gray-50 rounded-lg flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <FileText className="w-4 h-4 text-gray-500" />
                <span className="text-sm text-gray-700">{file.name}</span>
                {fileProcessed && (
                  <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                    Processed
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={onFileRemove}
                className="text-gray-400 hover:text-gray-600"
                disabled={fileProcessing}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            
            {!fileProcessed && (
              <button
                type="button"
                onClick={onProcessFile}
                disabled={fileProcessing}
                className="w-full inline-flex items-center justify-center px-4 py-2 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {fileProcessing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Processing with AI...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2" />
                    Process File with AI
                  </>
                )}
              </button>
            )}
            
            {fileProcessed && (
              <div className="text-center">
                <p className="text-sm text-green-700 font-medium">
                  ✅ File processed successfully! 
                </p>
                <p className="text-xs text-gray-600 mt-1">
                  The form below has been populated with the extracted data. You can review and modify it before creating the test case.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
