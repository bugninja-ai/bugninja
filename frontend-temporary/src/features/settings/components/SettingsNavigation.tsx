import React from 'react';
import { Settings as SettingsIcon, Monitor, Key, Globe, Eye } from 'lucide-react';

export type SettingsSection = 'project' | 'browser-configs' | 'secret-values' | 'view-preferences' | 'global' | 'integrations';

interface NavigationItem {
  id: SettingsSection;
  name: string;
  icon: React.ComponentType<any>;
  description: string;
  disabled?: boolean;
}

interface SettingsNavigationProps {
  activeSection: SettingsSection;
  onSectionChange: (section: SettingsSection) => void;
  projectName?: string;
}

const navigation: NavigationItem[] = [
  { id: 'project', name: 'Project Settings', icon: SettingsIcon, description: 'Change project name and default URL' },
  { id: 'browser-configs', name: 'Browser Configurations', icon: Monitor, description: 'View and manage browser configs' },
  { id: 'secret-values', name: 'Secret Values', icon: Key, description: 'View and manage project secrets' },
  { id: 'view-preferences', name: 'View Preferences', icon: Eye, description: 'Customize how you view lists and tables' },
  { id: 'global', name: 'Global Settings', icon: Globe, description: 'Application-wide settings', disabled: true },
  { id: 'integrations', name: 'Integrations', icon: SettingsIcon, description: 'Third-party integrations', disabled: true },
];

export const SettingsNavigation: React.FC<SettingsNavigationProps> = ({
  activeSection,
  onSectionChange,
  projectName
}) => {
  return (
    <div className="w-80 bg-white border border-dashed border-gray-300 rounded-xl m-4 flex flex-col overflow-hidden">
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-1">Manage settings for {projectName || 'your project'}</p>
      </div>
      
      <nav className="flex-1 p-4 space-y-2">
        {navigation.map((item) => {
          const Icon = item.icon;
          const isActive = activeSection === item.id;
          
          return (
            <button
              key={item.id}
              onClick={() => !item.disabled && onSectionChange(item.id)}
              disabled={item.disabled}
              className={`w-full text-left p-3 rounded-lg transition-colors flex items-start space-x-3 ${
                isActive
                  ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                  : item.disabled
                  ? 'text-gray-400 cursor-not-allowed'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${
                isActive ? 'text-indigo-600' : item.disabled ? 'text-gray-400' : 'text-gray-500'
              }`} />
              <div className="min-w-0">
                <div className="font-medium">{item.name}</div>
                <div className="text-sm text-gray-500 mt-1">{item.description}</div>
              </div>
            </button>
          );
        })}
      </nav>
    </div>
  );
};
