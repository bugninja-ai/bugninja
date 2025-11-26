import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, Globe, Edit, Lock, MousePointer, Clock, XCircle, User, Search, Play } from 'lucide-react';
import { BASE_DOMAIN } from '../services/api';

interface ScreenshotModalProps {
  isOpen: boolean;
  onClose: () => void;
  screenshot: string;
  actionData: {
    actionType: string;
    url?: string;
    xpath?: string;
    inputText?: string;
    status: 'passed' | 'failed';
    icon?: string;
    isSecret?: boolean;
  };
}

const ScreenshotModal: React.FC<ScreenshotModalProps> = ({ 
  isOpen, 
  onClose, 
  screenshot, 
  actionData 
}) => {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }

    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, onClose]);

  const getActionIcon = (actionType: string, iconName?: string) => {
    const iconMap: { [key: string]: React.ComponentType<any> } = {
      'go_to_url': Globe,
      'click_element_by_index': MousePointer,
      'input_text': Edit,
      'wait': Clock,
      'search_google': Search,
      'Navigate to URL': Globe,
      'Fill text input': Edit,
      'Fill password input': Lock,
      'Click login button': MousePointer,
      'Wait for page load': Clock,
      'Close popup dialog': XCircle,
      'Click user profile': User,
      'Wait for menu': Clock,
      'Search for settings': Search,
      'globe': Globe,
      'edit': Edit,
      'lock': Lock,
      'mouse-pointer': MousePointer,
      'clock': Clock,
      'x': XCircle,
      'user': User,
      'search': Search
    };
    
    const IconComponent = iconMap[iconName || actionType] || Play;
    return <IconComponent className="w-5 h-5" />;
  };

  if (!isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // Only close if clicking directly on the backdrop, not on child elements
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex" onClick={handleBackdropClick}>
      {/* Blurred background */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-md"
        onClick={handleBackdropClick}
      />
      
      {/* Modal content */}
      <div className="relative w-full h-full flex" onClick={(e) => e.stopPropagation()}>
        {/* Left side - Image */}
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="max-w-4xl max-h-full">
            <img
              src={`${BASE_DOMAIN}/${screenshot}`}
              alt="Screenshot"
              className="max-w-full max-h-full object-contain rounded-2xl shadow-2xl border border-white/20"
              style={{ maxHeight: 'calc(100vh - 4rem)' }}
            />
          </div>
        </div>
        
        {/* Right side - Action details */}
        <div className="w-96 bg-white/90 backdrop-blur-xl border-l border-gray-200/50 p-6 overflow-y-auto">
          {/* Close button */}
          <div className="flex justify-end mb-6">
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>
          
          {/* Action header */}
          <div className="mb-6">
            <div className="flex items-center space-x-3 mb-3">
              <div className="p-2 bg-indigo-100 rounded-lg">
                {getActionIcon(actionData.actionType, actionData.icon)}
              </div>
              <div>
                <h3 className="font-semibold text-gray-800">{actionData.actionType}</h3>
                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${
                  actionData.status === 'passed' 
                    ? 'text-green-600 bg-green-50 border-green-200' 
                    : 'text-red-600 bg-red-50 border-red-200'
                }`}>
                  {actionData.status.toUpperCase()}
                </span>
              </div>
            </div>
          </div>
          
          {/* Action details */}
          <div className="space-y-4">
            {actionData.url && (
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <label className="block text-sm font-medium text-gray-700 mb-2">URL</label>
                <div className="text-sm text-gray-800 break-all font-mono bg-white px-3 py-2 rounded border">
                  {actionData.url}
                </div>
              </div>
            )}
            
            {actionData.xpath && actionData.xpath !== 'N/A' && (
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <label className="block text-sm font-medium text-gray-700 mb-2">XPath</label>
                <div className="text-sm text-gray-800 break-all font-mono bg-white px-3 py-2 rounded border">
                  {actionData.xpath}
                </div>
              </div>
            )}
            
            {actionData.inputText && (
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <label className="block text-sm font-medium text-gray-700 mb-2">Input Text</label>
                <div className="text-sm text-gray-800 bg-white px-3 py-2 rounded border flex items-center space-x-2">
                  {actionData.isSecret && <Lock className="w-4 h-4 text-gray-600" />}
                  <span>{actionData.inputText}</span>
                </div>
              </div>
            )}
            

          </div>
          
          {/* Screenshot info */}
          <div className="mt-6 pt-6 border-t border-gray-200">
            <h4 className="font-medium text-gray-700 mb-2">Screenshot</h4>
            <p className="text-sm text-gray-600 break-all font-mono leading-relaxed">{screenshot}</p>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};

export { ScreenshotModal };
export default ScreenshotModal; 