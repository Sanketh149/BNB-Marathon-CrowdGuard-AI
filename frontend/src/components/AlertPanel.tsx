import {
  AlertTriangle,
  CloudRain,
  Calendar,
  Radio,
  Shield,
} from "lucide-react";

interface AgentPrediction {
  consolidated_risk_level?: string;
  summary?: string;
  correlation_analysis?: string;
  contributing_factors?: {
    ml_stats?: any;
    external_context?: {
      scheduled_events?: any[];
      social_media_reports?: any[];
      weather_conditions?: any;
      nearby_incidents?: any[];
    };
  };
  recommended_actions?: string[];
}

interface AlertPanelProps {
  agentPrediction: AgentPrediction | null;
}

// Mock data for fallback
const MOCK_DATA = {
  consolidated_risk_level: "Medium",
  summary: "Analysis in progress. Using mock data for display.",
  correlation_analysis: "No correlation data available yet.",
  external_context: {
    scheduled_events: [],
    social_media_reports: [],
    weather_conditions: null,
    nearby_incidents: [],
  },
  recommended_actions: [
    "Monitor crowd density continuously",
    "Prepare emergency response teams",
    "Maintain clear communication channels",
  ],
};

export default function AlertPanel({ agentPrediction }: AlertPanelProps) {
  // Safe accessors with fallback to mock data
  const riskLevel =
    agentPrediction?.consolidated_risk_level ||
    MOCK_DATA.consolidated_risk_level;
  const summary = agentPrediction?.summary || MOCK_DATA.summary;
  const correlationAnalysis =
    agentPrediction?.correlation_analysis || MOCK_DATA.correlation_analysis;
  const externalContext =
    agentPrediction?.contributing_factors?.external_context ||
    MOCK_DATA.external_context;
  const recommendedActions =
    agentPrediction?.recommended_actions || MOCK_DATA.recommended_actions;
  const getRiskColor = (level: string) => {
    const normalized = level?.toUpperCase() || "LOW";
    switch (normalized) {
      case "CRITICAL":
        return "bg-red-500/10 border-red-500 text-red-500";
      case "HIGH":
        return "bg-orange-500/10 border-orange-500 text-orange-500";
      case "MEDIUM":
        return "bg-yellow-500/10 border-yellow-500 text-yellow-500";
      default:
        return "bg-green-500/10 border-green-500 text-green-500";
    }
  };

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-800 h-[500px] flex flex-col">
      <div className="p-4 border-b border-slate-800">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-orange-500" />
          AI Risk Assessment
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!agentPrediction ? (
          <div className="text-center text-slate-500 py-12">
            <AlertTriangle className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No risk assessment available</p>
            <p className="text-sm">Waiting for analysis...</p>
          </div>
        ) : (
          <>
            {/* Risk Level Badge */}
            <div className={`p-4 rounded-lg border ${getRiskColor(riskLevel)}`}>
              <div className="flex items-center gap-2 mb-2">
                <Shield className="h-5 w-5" />
                <span className="font-bold text-lg">
                  {riskLevel.toUpperCase()} RISK
                </span>
              </div>
              <p className="text-sm opacity-90">{summary}</p>
            </div>

            {/* External Context */}
            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
              <h4 className="font-semibold mb-3 flex items-center gap-2">
                <Radio className="h-4 w-4 text-blue-500" />
                External Context
              </h4>

              <div className="space-y-3 text-sm">
                {/* Weather */}
                {externalContext.weather_conditions && (
                  <div>
                    <div className="flex items-center gap-2 text-cyan-400 mb-1">
                      <CloudRain className="h-3 w-3" />
                      <span className="font-semibold">Weather</span>
                    </div>
                    <p className="text-slate-400 ml-5">
                      {externalContext.weather_conditions.summary ||
                        "No weather data available"}
                    </p>
                    {externalContext.weather_conditions.alerts?.map(
                      (alert: string, idx: number) => (
                        <p
                          key={idx}
                          className="text-yellow-400 ml-5 text-xs mt-1"
                        >
                          ⚠️ {alert}
                        </p>
                      )
                    )}
                  </div>
                )}

                {/* Scheduled Events */}
                <div>
                  <div className="flex items-center gap-2 text-purple-400 mb-1">
                    <Calendar className="h-3 w-3" />
                    <span className="font-semibold">Scheduled Events</span>
                  </div>
                  <p className="text-slate-400 ml-5">
                    {(externalContext.scheduled_events?.length || 0) > 0
                      ? externalContext.scheduled_events
                          ?.map((e: any) => e.name || e)
                          .join(", ")
                      : "No scheduled events detected"}
                  </p>
                </div>

                {/* Social Media */}
                <div>
                  <div className="flex items-center gap-2 text-green-400 mb-1">
                    <Radio className="h-3 w-3" />
                    <span className="font-semibold">Social Media</span>
                  </div>
                  <p className="text-slate-400 ml-5">
                    {(externalContext.social_media_reports?.length || 0) > 0
                      ? externalContext.social_media_reports?.join(", ")
                      : "No social media reports"}
                  </p>
                </div>

                {/* Nearby Incidents */}
                <div>
                  <div className="flex items-center gap-2 text-red-400 mb-1">
                    <AlertTriangle className="h-3 w-3" />
                    <span className="font-semibold">Nearby Incidents</span>
                  </div>
                  <p className="text-slate-400 ml-5">
                    {(externalContext.nearby_incidents?.length || 0) > 0
                      ? externalContext.nearby_incidents?.join(", ")
                      : "No nearby incidents reported"}
                  </p>
                </div>
              </div>
            </div>

            {/* Correlation Analysis */}
            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
              <h4 className="font-semibold mb-2 text-purple-400">
                Correlation Analysis
              </h4>
              <p className="text-sm text-slate-400">{correlationAnalysis}</p>
            </div>

            {/* Recommended Actions */}
            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
              <h4 className="font-semibold mb-3 text-orange-400">
                Recommended Actions
              </h4>
              <ul className="space-y-2 text-sm">
                {recommendedActions.map((action, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-orange-400 mt-1">•</span>
                    <span className="text-slate-300">{action}</span>
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
