import React from 'react';
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  Globe,
  MousePointer,
  Edit,
  Lock,
  User,
  Search,
  Play
} from 'lucide-react';

export const getStatusColor = (status: string) => {
  switch (status.toLowerCase()) {
    case 'passed':
    case 'finished':
      return 'bg-emerald-100 text-emerald-800 border-emerald-200';
    case 'failed':
      return 'bg-red-100 text-red-800 border-red-200';
    case 'pending':
      return 'bg-amber-100 text-amber-800 border-amber-200';
    case 'skipped':
      return 'bg-gray-100 text-gray-800 border-gray-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
};

export const getStatusIcon = (status: string) => {
  switch (status.toLowerCase()) {
    case 'passed':
    case 'finished':
      return <CheckCircle className="w-4 h-4 text-emerald-500" />;
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-500" />;
    case 'pending':
      return <Clock className="w-4 h-4 text-amber-500" />;
    default:
      return <Clock className="w-4 h-4 text-amber-500" />;
  }
};

export const formatDate = (date: Date) => {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date));
};

export const formatDuration = (seconds: number) => {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
};

export const getActionIcon = (actionType: string, iconName?: string) => {
  const iconMap: { [key: string]: React.ComponentType<any> } = {
    // Legacy action types
    'go_to_url': Globe,
    'click_element_by_index': MousePointer,
    'input_text': Edit,
    'wait': Clock,
    'search_google': Search,
    // New proper action names
    'Navigate to URL': Globe,
    'Fill text input': Edit,
    'Fill password input': Lock,
    'Fill password/secret input': Lock,
    'Click login button': MousePointer,
    'Click element': MousePointer,
    'Wait for page load': Clock,
    'Close popup dialog': XCircle,
    'Click user profile': User,
    'Wait for menu': Clock,
    'Search for settings': Search,
    'Test completed': CheckCircle,
    // Icon name mappings
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
  return <IconComponent className="w-4 h-4 text-indigo-600" />;
};
