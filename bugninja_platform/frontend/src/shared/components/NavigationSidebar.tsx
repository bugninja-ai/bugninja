import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  FileText, 
  Upload, 
  History, 
  Settings,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
  X,
  FolderOpen,
  Github,
  LucideIcon
} from 'lucide-react';

interface NavigationItem {
  name: string;
  href: string;
  icon: LucideIcon;
}

interface NavigationSidebarProps {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  sidebarMinimized: boolean;
  setSidebarMinimized: (minimized: boolean) => void;
  currentProject: { name: string } | null;
  projectDropdownComponent: React.ReactNode;
}

const navigation: NavigationItem[] = [
  { name: 'Test cases', href: '/', icon: FileText },
  { name: 'Create test', href: '/create', icon: Upload },
  { name: 'Test runs', href: '/runs', icon: History },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export const NavigationSidebar: React.FC<NavigationSidebarProps> = ({
  sidebarOpen,
  setSidebarOpen,
  sidebarMinimized,
  setSidebarMinimized,
  currentProject,
  projectDropdownComponent
}) => {
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === '/' && location.pathname === '/') return true;
    
    // Handle test case detail pages - show Test cases as active
    if (path === '/' && location.pathname.startsWith('/test-details/')) return true;
    
    // Handle test run detail pages - show Test runs as active  
    if (path === '/runs' && location.pathname.startsWith('/runs/')) return true;
    
    return location.pathname === path;
  };

  const sidebarWidth = sidebarMinimized ? 'w-20' : 'w-72';

  return (
    <div className={`fixed left-0 top-0 h-full ${sidebarWidth} bg-white/80 backdrop-blur-xl border-r border-dashed border-gray-300 z-50 transform transition-all duration-300 ease-in-out ${
      sidebarOpen ? 'translate-x-0' : '-translate-x-full'
    } lg:translate-x-0`}
         style={{ zoom: 0.9 }}>
      
      {/* Logo and controls */}
      {!sidebarMinimized && (
        <div className="flex items-center justify-between px-6 py-3">
          <div className="flex items-center">
            <img 
              src="/bugninja.svg" 
              alt="Bugninja" 
              className="transition-all duration-300 w-24 h-10" 
            />
          </div>
          <div className="flex items-center space-x-2">
            {/* Minimize button (desktop only) */}
            <button
              onClick={() => setSidebarMinimized(!sidebarMinimized)}
              className="hidden lg:flex w-12 h-12 items-center justify-center rounded-lg hover:bg-gray-100 transition-colors"
              title="Minimize sidebar"
            >
              <ChevronLeft className="w-5 h-5 text-gray-500" />
            </button>
            {/* Close button (mobile only) */}
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden w-12 h-12 flex items-center justify-center rounded-lg hover:bg-gray-100 transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>
        </div>
      )}
      
      {/* Minimized expand button */}
      {sidebarMinimized && (
        <div className="px-2 py-1 pt-3">
          <button
            onClick={() => setSidebarMinimized(false)}
            className="w-12 h-12 flex items-center justify-center rounded-lg hover:bg-gray-100 transition-colors mx-auto"
            title="Expand sidebar"
          >
            <ChevronRight className="w-5 h-5 text-gray-500" />
          </button>
        </div>
      )}

      {/* Dashed separator */}
      <div className={`mb-4 ${sidebarMinimized ? 'mx-4' : 'mx-4'}`}>
        <div className="border-t border-dashed border-gray-300"></div>
      </div>

      {/* Project Selector */}
      {!sidebarMinimized && (
        <div className="px-4 mb-4">
          {projectDropdownComponent}
        </div>
      )}
      
      {/* Project selector for minimized state */}
      {sidebarMinimized && (
        <div className="flex justify-center">
          <button
            onClick={() => setSidebarMinimized(false)}
            className="w-12 h-12 flex items-center justify-center rounded-lg hover:bg-gray-100 transition-colors"
            title={currentProject?.name || 'Select Project'}
          >
            <FolderOpen className="w-5 h-5 text-gray-500" />
          </button>
        </div>
      )}

      {/* Navigation */}
      <nav className="px-4 space-y-1">
        {navigation.map((item) => {
          const Icon = item.icon;
          const active = isActive(item.href);
          
          return (
            <Link
              key={item.name}
              to={item.href}
              onClick={() => setSidebarOpen(false)}
              className={`flex items-center ${
                sidebarMinimized 
                  ? 'justify-center w-12 h-12 mx-auto' 
                  : 'space-x-3 px-4 py-3'
              } rounded-lg transition-colors group ${
                active 
                  ? 'bg-indigo-600 text-white' 
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`}
              title={sidebarMinimized ? item.name : undefined}
            >
              <Icon className={`w-5 h-5 flex-shrink-0 ${active ? 'text-white' : 'text-gray-500 group-hover:text-gray-700'}`} />
              {!sidebarMinimized && (
                <span className="font-medium whitespace-nowrap">{item.name}</span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Bottom section */}
      <div className="absolute bottom-0 left-0 right-0 p-3">
        <div className="border-t border-dashed border-gray-300 pt-3 space-y-1">
          {/* Star us on Github */}
          <a
            href="https://github.com/bugninja-ai/bugninja-platform"
            target="_blank"
            rel="noopener noreferrer"
            className={`flex items-center ${
              sidebarMinimized 
                ? 'justify-center w-12 h-12 mx-auto' 
                : 'space-x-3 px-4 py-3'
            } rounded-lg hover:bg-gray-100 transition-all duration-300 cursor-pointer group`}
            title={sidebarMinimized ? "Star us on Github" : undefined}
          >
            <Github className="w-5 h-5 text-gray-500 group-hover:text-gray-700 flex-shrink-0" />
            {!sidebarMinimized && (
              <span className="font-medium text-gray-600 group-hover:text-gray-900 whitespace-nowrap opacity-100 transition-all duration-300">Star us on Github</span>
            )}
          </a>
          
          {/* Help & Support */}
          <div className={`flex items-center ${
            sidebarMinimized 
              ? 'justify-center w-12 h-12 mx-auto' 
              : 'space-x-3 px-4 py-3'
          } rounded-lg hover:bg-gray-100 transition-all duration-300 cursor-pointer`}
          title={sidebarMinimized ? "Help & Support" : undefined}>
            <HelpCircle className="w-5 h-5 text-gray-500 flex-shrink-0" />
            {!sidebarMinimized && (
              <span className="font-medium text-gray-600 whitespace-nowrap opacity-100 transition-opacity duration-300">Help & Support</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
