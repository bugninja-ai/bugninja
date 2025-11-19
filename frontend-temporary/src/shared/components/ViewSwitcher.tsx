import React from 'react';
import { List, Table } from 'lucide-react';
import { ViewType } from './ViewPreferenceModal';

interface ViewSwitcherProps {
  currentView: ViewType;
  onViewChange: (view: ViewType) => void;
}

export const ViewSwitcher: React.FC<ViewSwitcherProps> = ({
  currentView,
  onViewChange,
}) => {
  return (
    <div className="inline-flex items-center bg-gray-100 rounded-lg p-1">
      <button
        onClick={() => onViewChange('list')}
        className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
          currentView === 'list'
            ? 'bg-white text-gray-900 shadow-sm'
            : 'text-gray-500 hover:text-gray-700'
        }`}
        title="List view"
      >
        <List className="w-4 h-4" />
      </button>
      <button
        onClick={() => onViewChange('table')}
        className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
          currentView === 'table'
            ? 'bg-white text-gray-900 shadow-sm'
            : 'text-gray-500 hover:text-gray-700'
        }`}
        title="Table view"
      >
        <Table className="w-4 h-4" />
      </button>
    </div>
  );
};
