import {
  Bot,
  ArrowRight,
  Clock,
  Database,
  Newspaper,
  TrendingUp,
} from "lucide-react";

interface AgentPrediction {
  consolidated_risk_level?: string;
  summary?: string;
  contributing_factors?: {
    ml_stats?: {
      analysis?: any;
      original_data?: any;
    };
    external_context?: any;
  };
}

interface AgentLogsProps {
  agentPrediction: AgentPrediction | null;
}

// Mock data for fallback
const MOCK_ML_DATA = {
  analysis: {
    justification: "No analysis available",
  },
  original_data: {
    timestamp: new Date().toISOString(),
    total_count: 0,
    density_score: 0,
    risk_level: "UNKNOWN",
    anomaly_type: "none",
    location: "Unknown",
    clusters: [],
  },
};

const MOCK_EXTERNAL_CONTEXT = {
  scheduled_events: [],
  social_media_reports: [],
};

export default function AgentLogs({ agentPrediction }: AgentLogsProps) {
  const formatTime = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString();
    } catch {
      return "--:--";
    }
  };

  // Safe accessors with fallback to mock data
  const mlStats =
    agentPrediction?.contributing_factors?.ml_stats || MOCK_ML_DATA;
  const originalData = mlStats?.original_data || MOCK_ML_DATA.original_data;
  const analysis = mlStats?.analysis || MOCK_ML_DATA.analysis;
  const externalContext =
    agentPrediction?.contributing_factors?.external_context ||
    MOCK_EXTERNAL_CONTEXT;

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-800 h-[500px] flex flex-col">
      <div className="p-4 border-b border-slate-800">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Bot className="h-5 w-5 text-purple-500" />
          Agent Analysis
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!agentPrediction ? (
          <div className="text-center text-slate-500 py-12">
            <Bot className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No agent activity</p>
            <p className="text-sm">Waiting for analysis...</p>
          </div>
        ) : (
          <>
            {/* ML Stats Analyzer */}
            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
              <div className="flex items-center gap-2 mb-3">
                <Database className="h-5 w-5 text-blue-500" />
                <span className="font-semibold text-blue-400">
                  ML Stats Analyzer
                </span>
                <span className="ml-auto text-xs text-slate-500 flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {formatTime(
                    originalData.timestamp || new Date().toISOString()
                  )}
                </span>
              </div>

              <div className="space-y-2 text-sm">
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-slate-900/50 p-2 rounded">
                    <div className="text-xs text-slate-500">Total Count</div>
                    <div className="text-lg font-bold text-blue-400">
                      {originalData.total_count || 0}
                    </div>
                  </div>
                  <div className="bg-slate-900/50 p-2 rounded">
                    <div className="text-xs text-slate-500">Density Score</div>
                    <div className="text-lg font-bold text-purple-400">
                      {(originalData.density_score || 0).toFixed(1)}
                    </div>
                  </div>
                  <div className="bg-slate-900/50 p-2 rounded">
                    <div className="text-xs text-slate-500">Risk Level</div>
                    <div className="text-lg font-bold text-orange-400">
                      {originalData.risk_level || "UNKNOWN"}
                    </div>
                  </div>
                  <div className="bg-slate-900/50 p-2 rounded">
                    <div className="text-xs text-slate-500">Anomaly</div>
                    <div className="text-sm font-bold text-yellow-400 capitalize">
                      {(originalData.anomaly_type || "none").replace("_", " ")}
                    </div>
                  </div>
                </div>

                <div className="mt-3 p-2 bg-slate-900/50 rounded">
                  <div className="text-xs text-slate-500 mb-1">Location</div>
                  <div className="text-slate-300">
                    {originalData.location || "Unknown"}
                  </div>
                </div>

                {(originalData.clusters?.length || 0) > 0 && (
                  <div className="mt-2 p-2 bg-slate-900/50 rounded">
                    <div className="text-xs text-slate-500 mb-1">
                      Detected Clusters
                    </div>
                    <div className="text-slate-400 text-xs">
                      {originalData.clusters.length} cluster(s) - Largest:{" "}
                      {originalData.clusters[0]?.size || 0} people
                    </div>
                  </div>
                )}

                <div className="mt-3 pt-3 border-t border-slate-700">
                  <div className="text-xs text-slate-500 mb-1">Analysis</div>
                  <div className="text-slate-300">
                    {analysis.justification || "No analysis available"}
                  </div>
                </div>
              </div>
            </div>

            {/* News Gatherer */}
            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
              <div className="flex items-center gap-2 mb-3">
                <Newspaper className="h-5 w-5 text-green-500" />
                <span className="font-semibold text-green-400">
                  News Gatherer
                </span>
                <span className="ml-auto text-xs text-slate-500 flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {formatTime(new Date().toISOString())}
                </span>
              </div>

              <div className="space-y-3 text-sm">
                <div>
                  <div className="text-xs text-slate-500 mb-1">
                    External Context Summary
                  </div>
                  <div className="text-slate-300">
                    Analyzed weather conditions, scheduled events, social media
                    reports, and nearby incidents.
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-slate-900/50 p-2 rounded">
                    <div className="text-xs text-slate-500">Events</div>
                    <div className="text-lg font-bold text-purple-400">
                      {externalContext.scheduled_events?.length || 0}
                    </div>
                  </div>
                  <div className="bg-slate-900/50 p-2 rounded">
                    <div className="text-xs text-slate-500">Reports</div>
                    <div className="text-lg font-bold text-cyan-400">
                      {externalContext.social_media_reports?.length || 0}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Risk Correlation */}
            <div className="p-4 rounded-lg bg-gradient-to-br from-purple-500/10 to-orange-500/10 border border-purple-500/30">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="h-5 w-5 text-purple-400" />
                <span className="font-semibold text-purple-300">
                  Stampede Predictor
                </span>
              </div>
              <div className="text-sm text-slate-300">
                <div className="text-xs text-purple-400 mb-1">
                  FINAL ASSESSMENT
                </div>
                <div>
                  Risk Level:{" "}
                  <span className="font-bold">
                    {(
                      agentPrediction?.consolidated_risk_level || "UNKNOWN"
                    ).toUpperCase()}
                  </span>
                </div>
                <div className="mt-2 text-xs text-slate-400">
                  Combined analysis from ML detection and external context
                  monitoring.
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
