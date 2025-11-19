import React from 'react';
import { Edit, Save, X } from 'lucide-react';

interface EditableSectionProps {
  title: string;
  isEditing: boolean;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
  children: React.ReactNode;
  className?: string;
  editTitle?: string;
}

export const EditableSection: React.FC<EditableSectionProps> = ({
  title,
  isEditing,
  onEdit,
  onSave,
  onCancel,
  children,
  className = '',
  editTitle = `Edit ${title.toLowerCase()}`
}) => {
  return (
    <div className={`bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800">{title}</h2>
        <div className="flex items-center space-x-2">
          {isEditing ? (
            <>
              <button
                onClick={onSave}
                className="inline-flex items-center px-3 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
              >
                <Save className="w-4 h-4 mr-1" />
                Save
              </button>
              <button
                onClick={onCancel}
                className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                <X className="w-4 h-4 mr-1" />
                Cancel
              </button>
            </>
          ) : (
            <button
              onClick={onEdit}
              className="inline-flex items-center p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              title={editTitle}
            >
              <Edit className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
      {children}
    </div>
  );
};
