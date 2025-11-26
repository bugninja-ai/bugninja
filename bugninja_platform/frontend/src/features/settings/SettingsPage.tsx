import React, { useState } from 'react';
import { Settings as SettingsIcon } from 'lucide-react';
import { useProjects } from '../../shared/hooks/useProjects';
import { SettingsNavigation, SettingsSection } from './components/SettingsNavigation';
import { ProjectSettingsSection } from './components/ProjectSettingsSection';
import { BrowserConfigsSection } from './components/BrowserConfigsSection';
import { SecretValuesSection } from './components/SecretValuesSection';
import { ViewPreferencesSection } from './components/ViewPreferencesSection';

const SettingsPage: React.FC = () => {
  const [activeSection, setActiveSection] = useState<SettingsSection>('project');
  const { selectedProject } = useProjects();

  const renderContent = () => {
    switch (activeSection) {
      case 'project':
        return <ProjectSettingsSection />;

      case 'browser-configs':
        return <BrowserConfigsSection />;

      case 'secret-values':
        return <SecretValuesSection />;

      case 'view-preferences':
        return <ViewPreferencesSection />;

      default:
        return (
          <div className="text-center py-12">
            <SettingsIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Coming Soon</h3>
            <p className="text-gray-600">This section is under development.</p>
          </div>
        );
    }
  };

  return (
    <div className="flex h-full bg-gray-50">
      {/* Sidebar */}
      <SettingsNavigation
        activeSection={activeSection}
        onSectionChange={setActiveSection}
        projectName={selectedProject?.name}
      />

      {/* Main Content */}
      <div className="flex-1 p-8 overflow-y-auto">
        {renderContent()}
      </div>
    </div>
  );
};

export default SettingsPage;
