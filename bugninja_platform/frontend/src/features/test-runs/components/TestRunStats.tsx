import React from 'react';
import { Play, CheckCircle, Clock } from 'lucide-react';
import { StatsCard } from '../../../shared/components/StatsCard';

interface TestRunStatsProps {
  totalCount: number;
  testRuns: any[] | null;
  filteredRuns: any[];
  isBrowserFiltered: boolean;
}

const formatDuration = (seconds: number) => {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  } else {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  }
};

export const TestRunStats: React.FC<TestRunStatsProps> = ({
  totalCount,
  testRuns,
  filteredRuns,
  isBrowserFiltered
}) => {
  // Calculate success rate
  const runsToCheck = isBrowserFiltered ? filteredRuns : testRuns;
  const successRate = runsToCheck && runsToCheck.length > 0 
    ? Math.round((runsToCheck.filter(r => r.current_state === 'FINISHED').length / runsToCheck.length) * 100)
    : 0;

  // Calculate average duration
  const avgDuration = runsToCheck && runsToCheck.length > 0 
    ? formatDuration(runsToCheck.reduce((acc: number, run: any) => acc + (run.duration || 0), 0) / runsToCheck.length)
    : '0s';

  const displayCount = isBrowserFiltered ? filteredRuns.length : totalCount;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <StatsCard
        title="Total runs"
        value={displayCount}
        icon={Play}
        iconColor="text-indigo-600"
        iconBgColor="bg-indigo-100"
        subtitle={isBrowserFiltered ? 'Filtered results' : 'Last 30 days'}
        subtitleColor="text-indigo-600 font-medium"
      />

      <StatsCard
        title="Success rate"
        value={`${successRate}%`}
        icon={CheckCircle}
        iconColor="text-emerald-600"
        iconBgColor="bg-emerald-100"
        subtitle={
          <>
            <span className="text-emerald-600 font-medium">+5%</span>
            <span className="text-gray-600 ml-1">from last week</span>
          </>
        }
      />

      <StatsCard
        title="Avg duration"
        value={avgDuration}
        icon={Clock}
        iconColor="text-blue-600"
        iconBgColor="bg-blue-100"
        subtitle="Improving"
        subtitleColor="text-blue-600 font-medium"
      />
    </div>
  );
};
