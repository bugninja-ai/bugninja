import React, { useState, useEffect } from 'react';
import { List, Table, Save } from 'lucide-react';
import { ViewType } from '../../../shared/components';

export const ViewPreferencesSection: React.FC = () => {
  const [testCasesView, setTestCasesView] = useState<ViewType>('list');
  const [testRunsView, setTestRunsView] = useState<ViewType>('list');
  const [hasChanges, setHasChanges] = useState(false);

  // Load current preferences from localStorage
  useEffect(() => {
    const savedTestCasesView = localStorage.getItem('testCasesViewPreference') as ViewType;
    const savedTestRunsView = localStorage.getItem('testRunsViewPreference') as ViewType;
    
    if (savedTestCasesView) {
      setTestCasesView(savedTestCasesView);
    }
    if (savedTestRunsView) {
      setTestRunsView(savedTestRunsView);
    }
  }, []);

  // Check for changes
  useEffect(() => {
    const currentTestCasesView = localStorage.getItem('testCasesViewPreference') as ViewType || 'list';
    const currentTestRunsView = localStorage.getItem('testRunsViewPreference') as ViewType || 'list';
    
    setHasChanges(
      testCasesView !== currentTestCasesView || 
      testRunsView !== currentTestRunsView
    );
  }, [testCasesView, testRunsView]);

  const handleSave = () => {
    localStorage.setItem('testCasesViewPreference', testCasesView);
    localStorage.setItem('testRunsViewPreference', testRunsView);
    setHasChanges(false);
    
    // Show a brief success message or refresh the page to apply changes
    window.location.reload();
  };

  const ViewOption = ({ 
    title, 
    description, 
    icon: Icon,
    selected,
    onClick 
  }: {
    title: string;
    description: string;
    icon: React.ComponentType<any>;
    selected: boolean;
    onClick: () => void;
  }) => (
    <button
      onClick={onClick}
      className={`group relative border-2 rounded-lg p-4 text-left transition-all duration-200 ${
        selected 
          ? 'border-indigo-500 bg-indigo-50' 
          : 'border-gray-200 hover:border-indigo-300 hover:bg-indigo-50'
      }`}
    >
      <div className="flex items-center space-x-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
          selected 
            ? 'bg-indigo-100' 
            : 'bg-gray-100 group-hover:bg-indigo-100'
        }`}>
          <Icon className={`w-5 h-5 ${
            selected 
              ? 'text-indigo-600' 
              : 'text-gray-600 group-hover:text-indigo-600'
          }`} />
        </div>
        <div>
          <h4 className={`font-medium ${
            selected 
              ? 'text-indigo-900' 
              : 'text-gray-900 group-hover:text-indigo-900'
          }`}>
            {title}
          </h4>
          <p className={`text-sm ${
            selected 
              ? 'text-indigo-700' 
              : 'text-gray-500 group-hover:text-indigo-700'
          }`}>
            {description}
          </p>
        </div>
      </div>
    </button>
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">View Preferences</h2>
        <p className="text-gray-600">Customize how you view lists and tables across the platform</p>
      </div>

      {/* Test Cases View Preference */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Test Cases View</h3>
        <p className="text-sm text-gray-600 mb-4">Choose how you prefer to view your test cases</p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ViewOption
            title="List View"
            description="Detailed cards with full information"
            icon={List}
            selected={testCasesView === 'list'}
            onClick={() => setTestCasesView('list')}
          />
          <ViewOption
            title="Table View"
            description="Compact table with 25 items per page"
            icon={Table}
            selected={testCasesView === 'table'}
            onClick={() => setTestCasesView('table')}
          />
        </div>
      </div>

      {/* Test Runs View Preference */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Test Runs View</h3>
        <p className="text-sm text-gray-600 mb-4">Choose how you prefer to view your test runs</p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ViewOption
            title="List View"
            description="Detailed cards with execution information"
            icon={List}
            selected={testRunsView === 'list'}
            onClick={() => setTestRunsView('list')}
          />
          <ViewOption
            title="Table View"
            description="Compact table with 25 items per page"
            icon={Table}
            selected={testRunsView === 'table'}
            onClick={() => setTestRunsView('table')}
          />
        </div>
      </div>

      {/* Save Button */}
      {hasChanges && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-medium text-gray-900">Save Changes</h3>
              <p className="text-sm text-gray-600">You have unsaved view preference changes</p>
            </div>
            <button
              onClick={handleSave}
              className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
            >
              <Save className="w-4 h-4 mr-2" />
              Save Preferences
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
