import React from 'react';
import { CheckCircle, Clock, X, AlertCircle } from 'lucide-react';

export type StatusType = 'passed' | 'failed' | 'pending' | 'finished';

interface StatusBadgeProps {
  status: StatusType | string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '' }) => {
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'passed':
      case 'finished':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'failed':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'pending':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    const normalizedStatus = status.toLowerCase();
    switch (normalizedStatus) {
      case 'passed':
      case 'finished':
        return <CheckCircle className="w-4 h-4 text-emerald-500" />;
      case 'failed':
        return <X className="w-4 h-4 text-red-500" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-amber-500" />;
      default:
        return <AlertCircle className="w-4 h-4 text-amber-500" />;
    }
  };

  return (
    <span className={`inline-flex items-center space-x-1 text-xs font-semibold px-2.5 py-1 rounded-full border ${getStatusColor(status)} ${className}`}>
      {getStatusIcon(status)}
      <span>{status.charAt(0).toUpperCase() + status.slice(1)}</span>
    </span>
  );
};
