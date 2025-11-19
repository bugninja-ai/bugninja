import React from 'react';
import { X, List, Table } from 'lucide-react';

export type ViewType = 'list' | 'table';

interface ViewPreferenceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectView: (viewType: ViewType) => void;
  onDontShowAgain: () => void;
}

export const ViewPreferenceModal: React.FC<ViewPreferenceModalProps> = ({
  isOpen,
  onClose,
  onSelectView,
  onDontShowAgain,
}) => {
  const handleSelectView = (viewType: ViewType) => {
    // Always mark as shown when user makes a selection
    onDontShowAgain();
    onSelectView(viewType);
    onClose();
  };

  const handleClose = () => {
    // Mark as shown even if user just closes without selecting
    onDontShowAgain();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="modal-backdrop fixed bg-black bg-opacity-50 z-[10000]"
        style={{ 
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          width: '100vw',
          height: '100vh',
          margin: 0,
          padding: 0
        }}
        onClick={handleClose}
      />
      
      {/* Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-[10001] p-4">
        <div className="bg-white rounded-lg shadow-xl w-full max-w-lg">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Choose your preferred view</h2>
              <p className="text-sm text-gray-500">Select how you'd like to see test cases and test runs. You can change this later in settings.</p>
            </div>
            <button
              onClick={handleClose}
              className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 transition-colors"
            >
              <X className="w-4 h-4 text-gray-500" />
            </button>
          </div>
          
          {/* Content */}
          <div className="p-6 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* List View Option */}
              <button
                onClick={() => handleSelectView('list')}
                className="group relative border-2 border-gray-200 rounded-lg p-6 hover:border-indigo-300 hover:bg-indigo-50 transition-all duration-200 text-left"
              >
                <div className="flex flex-col items-center space-y-3">
                  <div className="w-12 h-12 bg-gray-100 group-hover:bg-indigo-100 rounded-lg flex items-center justify-center">
                    <List className="w-6 h-6 text-gray-600 group-hover:text-indigo-600" />
                  </div>
                  <div className="text-center">
                    <h3 className="font-medium text-gray-900 group-hover:text-indigo-900">List View</h3>
                    <p className="text-sm text-gray-500 group-hover:text-indigo-700 mt-1">
                      Scrollable cards with detailed information
                    </p>
                  </div>
                </div>
              </button>

              {/* Table View Option */}
              <button
                onClick={() => handleSelectView('table')}
                className="group relative border-2 border-gray-200 rounded-lg p-6 hover:border-indigo-300 hover:bg-indigo-50 transition-all duration-200 text-left"
              >
                <div className="flex flex-col items-center space-y-3">
                  <div className="w-12 h-12 bg-gray-100 group-hover:bg-indigo-100 rounded-lg flex items-center justify-center">
                    <Table className="w-6 h-6 text-gray-600 group-hover:text-indigo-600" />
                  </div>
                  <div className="text-center">
                    <h3 className="font-medium text-gray-900 group-hover:text-indigo-900">Table View</h3>
                    <p className="text-sm text-gray-500 group-hover:text-indigo-700 mt-1">
                      Compact table with sortable columns
                    </p>
                  </div>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};
