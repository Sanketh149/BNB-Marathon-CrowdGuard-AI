import { Users, Activity, AlertTriangle, TrendingUp } from "lucide-react";

interface MetricsCardsProps {
  metrics: {
    maxPeople: number;
    averageDensity: number;
    activeAlerts: number;
    riskLevel: string;
  };
}

export default function MetricsCards({ metrics }: MetricsCardsProps) {
  const getRiskColor = (level: string) => {
    switch (level) {
      case "CRITICAL":
        return "text-red-500 bg-red-500/10 border-red-500";
      case "HIGH":
        return "text-orange-500 bg-orange-500/10 border-orange-500";
      case "MEDIUM":
        return "text-yellow-500 bg-yellow-500/10 border-yellow-500";
      default:
        return "text-green-500 bg-green-500/10 border-green-500";
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Total People */}
      <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <div className="p-3 bg-blue-500/10 rounded-lg">
            <Users className="h-6 w-6 text-blue-500" />
          </div>
          <TrendingUp className="h-4 w-4 text-slate-500" />
        </div>
        <div>
          <div className="text-3xl font-bold mb-1">{metrics.maxPeople}</div>
          <div className="text-sm text-slate-400">Max People Detected</div>
        </div>
      </div>

      {/* Density Score */}
      <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <div className="p-3 bg-purple-500/10 rounded-lg">
            <Activity className="h-6 w-6 text-purple-500" />
          </div>
          <div className="text-sm text-slate-400">/ 100</div>
        </div>
        <div>
          <div className="text-3xl font-bold mb-1">
            {metrics.averageDensity.toFixed(1)}
          </div>
          <div className="text-sm text-slate-400">Density Score</div>
        </div>
      </div>

      {/* Active Alerts */}
      <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <div className="p-3 bg-orange-500/10 rounded-lg">
            <AlertTriangle className="h-6 w-6 text-orange-500" />
          </div>
          {metrics.activeAlerts > 0 && (
            <span className="px-2 py-1 bg-red-500 text-xs rounded-full animate-pulse">
              ACTIVE
            </span>
          )}
        </div>
        <div>
          <div className="text-3xl font-bold mb-1">{metrics.activeAlerts}</div>
          <div className="text-sm text-slate-400">Active Alerts</div>
        </div>
      </div>

      {/* Risk Level */}
      <div
        className={`rounded-lg p-6 border ${getRiskColor(metrics.riskLevel)}`}
      >
        <div className="flex items-center justify-between mb-4">
          <div className="p-3 bg-current/10 rounded-lg">
            <AlertTriangle className="h-6 w-6" />
          </div>
        </div>
        <div>
          <div className="text-3xl font-bold mb-1">{metrics.riskLevel}</div>
          <div className="text-sm opacity-70">Risk Level</div>
        </div>
      </div>
    </div>
  );
}
