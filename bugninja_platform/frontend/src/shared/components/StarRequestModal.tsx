import React, { useState } from 'react';
import { X, Github } from 'lucide-react';

interface StarRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDontShowAgain: () => void;
}

export const StarRequestModal: React.FC<StarRequestModalProps> = ({
  isOpen,
  onClose,
  onDontShowAgain,
}) => {
  const [dontShowAgain, setDontShowAgain] = useState(false);

  const handleClose = () => {
    if (dontShowAgain) {
      onDontShowAgain();
    }
    onClose();
  };

  const handleStarClick = () => {
    // Open GitHub repository in new tab
    window.open('https://github.com/bugninja-ai/bugninja-platform', '_blank', 'noopener,noreferrer');
    handleClose();
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
        <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gray-900 rounded-lg flex items-center justify-center">
                <Github className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Help us with a star!</h2>
                <p className="text-sm text-gray-500">Help us grow by starring our repository</p>
              </div>
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
                         <div className="text-center">
               <div className="mb-4">
                 <img 
                   src="/bugninja-icon.png" 
                   alt="Bugninja" 
                   className="w-12 h-12 mx-auto mb-3" 
                 />
                 <h3 className="text-lg font-medium text-gray-900 mb-2">Enjoying Bugninja?</h3>
                 <p className="text-gray-600">
                   Sorry for being pushy, but we're a small team and we're trying to grow, if you like the project please give us a star on GitHub!
                 </p>
               </div>
              
              {/* Don't show again checkbox */}
              <div className="flex items-center justify-center space-x-2 mb-6 mt-16">
                <input
                  id="dont-show-again"
                  type="checkbox"
                  checked={dontShowAgain}
                  onChange={(e) => setDontShowAgain(e.target.checked)}
                  className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded accent-indigo-600"
                />
                <label htmlFor="dont-show-again" className="text-sm text-gray-600">
                  Don't show this again
                </label>
              </div>
            </div>
            
            {/* Actions */}
            <div className="flex items-center justify-end space-x-3">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
              >
                Maybe later
              </button>
              <button
                type="button"
                onClick={handleStarClick}
                className="px-4 py-2 text-sm font-medium text-white bg-black border border-transparent rounded-lg hover:bg-gray-800 focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 flex items-center space-x-2"
              >
                <Github className="w-4 h-4" />
                <span>Star us on GitHub</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};
