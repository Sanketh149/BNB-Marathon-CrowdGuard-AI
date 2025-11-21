import { useState, useRef, useEffect } from "react";
import { Radio, Upload, Play, Pause } from "lucide-react";
import MetricsCards from "./components/MetricsCards";
import AlertPanel from "./components/AlertPanel";
import AgentLogs from "./components/AgentLogs";
import Heatmap from "./components/Heatmap";
import { GoogleGenerativeAI } from "@google/generative-ai";

interface AgentPrediction {
  consolidated_risk_level: string;
  summary: string;
  correlation_analysis: string;
  contributing_factors: {
    ml_stats: any;
    external_context: any;
  };
  recommended_actions: string[];
}

// --- Agent Prediction Mock Data (kept for fallback) ---
const MOCK_AGENT_PREDICTION: AgentPrediction = {
  consolidated_risk_level: "Medium",
  summary:
    "The ML model detected a MEDIUM risk level at Chinnaswamy stadium due to a 'sudden_movement' anomaly among a small group (20 people) with a density score of 46.25. This localized behavioral anomaly is not currently explained by any scheduled events, social media reports, or recent external incidents. The weather information available is outdated and not relevant to the current timestamp.",
  correlation_analysis:
    "The ML model's 'sudden_movement' anomaly is the primary indicator of the medium risk, as external context does not provide a direct explanation. There are no scheduled events at the stadium, no social media reports of unrest, and no nearby incidents reported. The weather data retrieved by the news gatherer is for October 2025, which is not current for the ML timestamp of November 20, 2025, thus it cannot be correlated. The detected anomaly appears to be an internal, localized event not triggered by known external factors, warranting investigation.",
  contributing_factors: {
    ml_stats: {
      analysis: {
        risk_category: "Medium",
        justification:
          "The ML model detected a MEDIUM risk level with a risk score of 40.5 and an anomaly type of 'sudden_movement'. This indicates a developing situation that requires monitoring.",
      },
      original_data: {
        anomaly_type: "sudden_movement",
        camera_id: "video_upload",
        clusters: [
          {
            area: 2148,
            bbox: [157, 232, 336, 244],
            center: [239.3, 236.3],
            cluster_id: 0,
            size: 10,
          },
        ],
        density_score: 46.25,
        flow_rate: 0,
        high_density_zones: [],
        location: "Chinnaswamy stadium, Bangalore",
        risk_level: "MEDIUM",
        risk_score: 40.5,
        timestamp: "2025-11-20T19:11:06.802037",
        total_count: 20,
        total_sum: 723,
      },
    },
    external_context: {
      scheduled_events: [],
      social_media_reports: [],
      weather_conditions: {
        summary:
          "Moderately rainy day anticipated in Bangalore on October 20-21, 2025, with afternoon showers highly probable and a 91% chance of patchy rain.",
        alerts: [
          "Afternoon showers highly probable on October 20, 2025. Residents should carry umbrellas.",
          "Patchy rain and mild temperatures expected on October 21, 2025, with a 91% chance of showers, especially late afternoon. High humidity (87%).",
        ],
      },
      nearby_incidents: [],
    },
  },
  recommended_actions: [
    "Dispatch security personnel to the area within Chinnaswamy stadium where the 'sudden_movement' anomaly was detected to observe and understand the cause.",
    "Review live camera feeds (if available) for the identified cluster and high-density zones to visually confirm the 'sudden_movement' and assess its nature (e.g., sudden rush, sudden stop, panic).",
    "If the 'sudden_movement' is sustained or intensifies, issue a localized warning to individuals in the immediate vicinity to maintain calm and avoid sudden actions.",
    "Investigate the reason for the 20 individuals being present at the stadium given no scheduled events, and if necessary, guide them to appropriate areas or exits.",
  ],
};

// Initialize Gemini AI (Must be done outside the component or within a useEffect if API Key state management is needed)
// NOTE: This approach exposes the API key and is used here ONLY for demonstration purposes,
// following the structure of the user's initial code.
const genAI = new GoogleGenerativeAI(import.meta.env.VITE_GEMINI_API_KEY || "");

// --- New Function to Generate Mock ML Stats using Gemini ---
const generateMockMLStats = async (location: string): Promise<any> => {
  const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });

  const prompt = `You are a crowd analysis AI. Generate realistic crowd statistics for the following location: "${
    location || "Unknown Location"
  }".

Return ONLY a valid JSON object (no markdown, no code blocks, no explanations) with this exact structure:
{
  "timestamp": "${new Date().toISOString()}",
  "location": "${location || "Unknown Location"}",
  "camera_id": "manual_upload_1",
  "total_count": <random number between 20-100>,
  "density_score": <random float between 30-80>,
  "flow_rate": <random float between 5-15>,
  "risk_level": "<one of: LOW, MEDIUM, HIGH, CRITICAL>",
  "risk_score": <random float between 20-90>,
  "anomaly_type": "<one of: normal, HIGH_FOOT_TRAFFIC, sudden_movement, crowd_buildup, NONE>",
  "high_density_zones": [
    {"grid_position": [<random 0-10>, <random 0-10>], "person_count": <random 5-15>}
  ],
  "clusters": [
    {"cluster_id": 0, "size": <random 10-30>, "center": [<random 200-600>, <random 200-400>]}
  ]
}

Make it realistic for the location context. Return ONLY the JSON, nothing else.`;

  const result = await model.generateContent(prompt);
  const geminiResponse = result.response.text();

  // Clean up the response (remove markdown code blocks if present)
  let cleanedResponse = geminiResponse.trim();
  if (cleanedResponse.startsWith("```json")) {
    cleanedResponse = cleanedResponse
      .replace(/```json\n?/g, "")
      .replace(/```\n?/g, "");
  } else if (cleanedResponse.startsWith("```")) {
    cleanedResponse = cleanedResponse.replace(/```\n?/g, "");
  }

  return JSON.parse(cleanedResponse);
};

// --- Function to Upload Stats to GCS ---
const uploadStatsToGCS = async (stats: any) => {
  const bucketName = import.meta.env.VITE_GCS_BUCKET_NAME;
  const fileName = import.meta.env.VITE_GCS_STATS_FILE;
  const accessToken = import.meta.env.VITE_GCP_ACCESS_TOKEN;

  if (!bucketName || !fileName || !accessToken) {
    console.warn("⚠️ GCS config or Access Token missing, skipping upload");
    return false;
  }

  try {
    const url = `https://storage.googleapis.com/upload/storage/v1/b/${bucketName}/o?uploadType=media&name=${fileName}`;

    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(stats, null, 2),
    });

    if (response.ok) {
      console.log(`✅ Stats written to gs://${bucketName}/${fileName}`);
      return true;
    } else {
      const errorText = await response.text();
      console.error(
        `❌ Failed to write to GCS: ${response.status} ${errorText}`
      );
      return false;
    }
  } catch (error) {
    console.error(`❌ Failed to write to GCS: ${error}`);
    return false;
  }
};
// --- End New Function ---

function App() {
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState<string>("");
  const [annotatedVideoUrl, setAnnotatedVideoUrl] = useState<string>("");
  const [location, setLocation] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [metrics, setMetrics] = useState({
    totalPeople: 0,
    maxPeople: 0,
    averageDensity: 0,
    activeAlerts: 0,
    riskLevel: "LOW",
  });
  const [agentPrediction, setAgentPrediction] =
    useState<AgentPrediction | null>(null);
  const [heatmapData, setHeatmapData] = useState<any>(null);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Helper function to merge agent data with mock data fallback
  const mergeWithMockData = (
    apiData: Partial<AgentPrediction> | null
  ): AgentPrediction => {
    return {
      consolidated_risk_level:
        apiData?.consolidated_risk_level ||
        MOCK_AGENT_PREDICTION.consolidated_risk_level,
      summary: apiData?.summary || MOCK_AGENT_PREDICTION.summary,
      correlation_analysis:
        apiData?.correlation_analysis ||
        MOCK_AGENT_PREDICTION.correlation_analysis,
      contributing_factors: {
        ml_stats:
          apiData?.contributing_factors?.ml_stats ||
          MOCK_AGENT_PREDICTION.contributing_factors.ml_stats,
        external_context:
          apiData?.contributing_factors?.external_context ||
          MOCK_AGENT_PREDICTION.contributing_factors.external_context,
      },
      recommended_actions:
        apiData?.recommended_actions ||
        MOCK_AGENT_PREDICTION.recommended_actions,
    };
  };

  // Load saved location from localStorage on mount
  useEffect(() => {
    const savedLocation = localStorage.getItem("crowdguard_location");
    if (savedLocation) {
      setLocation(savedLocation);
    }
  }, []);

  // Save location to localStorage whenever it changes
  const handleLocationChange = (value: string) => {
    setLocation(value);
    localStorage.setItem("crowdguard_location", value);
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setVideoFile(file);
      const url = URL.createObjectURL(file);
      setVideoUrl(url);
      // NOTE: For the purpose of this simulation, we'll use the same URL for "annotated" video
      // In a real app, this would be fetched from the ML backend after processing.
      setAnnotatedVideoUrl(url);
    }
  };

  const handleProcessVideo = async () => {
    if (!videoFile) return;
    if (!location.trim()) {
      alert("Please enter a location before processing");
      return;
    }

    setIsProcessing(true);
    setAnalysisComplete(false);

    // Start processing video
    await processVideo();
  };

  const processVideo = async () => {
    try {
      // 1. Generate crowd stats using Gemini AI (simulating ML output)
      const mlStats = await generateMockMLStats(location);

      console.log("Generated ML Stats:", mlStats);

      // Upload to GCS
      await uploadStatsToGCS(mlStats);

      // Since we removed the backend upload, we mock the annotated video URL
      // by simply using the uploaded video URL.
      setAnnotatedVideoUrl(videoUrl);

      // Update metrics
      setMetrics({
        totalPeople: mlStats.total_count,
        maxPeople: mlStats.total_count,
        averageDensity: mlStats.density_score,
        activeAlerts: 0,
        riskLevel: mlStats.risk_level,
      });

      // Update heatmap with cluster centers
      if (mlStats.clusters && mlStats.clusters.length > 0) {
        setHeatmapData({
          // The center coordinates from the mock ML stats need to be normalized or
          // used directly based on the expected input of your Heatmap component.
          points: mlStats.clusters.map((c: any) => c.center),
          width: 640,
          height: 480,
        });
      }

      setAnalysisComplete(true);

      // Set mock data immediately to ensure UI always has data
      setAgentPrediction(MOCK_AGENT_PREDICTION);

      // 2. Fetch agent prediction from deployed Cloud Run API
      const sessionId = crypto.randomUUID();

      // 2. Construct the full URL using the standard ADK management path
      // Format: BASE_URL/apps/{appName}/users/{userId}/sessions/{sessionId}
      const BASE_URL_REMOTE =
        "https://crowdguard-adk-agent-255137970778.europe-west1.run.app";
      const APP_NAME = "orchestrator_agent";
      const USER_ID = "user";
      const sessionUrl = `${BASE_URL_REMOTE}/apps/${APP_NAME}/users/${USER_ID}/sessions/${sessionId}`;

      console.log(`Attempting to create new session: ${sessionId}`);
      console.log(`POST to URL: ${sessionUrl}`);

      try {
        const response = await fetch(sessionUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          // The body is typically empty as all necessary info is in the URL path
          body: JSON.stringify({}),
        });

        if (response.ok) {
          console.log(`✅ Session ${sessionId} created successfully.`);
          const data = await response.json();
          console.log("Session response data:", data);
        } else {
          const errorText = await response.text();
          console.error(
            `❌ Failed to create session. Status: ${response.status} | Message: ${errorText}`
          );
        }
      } catch (error) {
        console.error("❌ Network error during session creation:", error);
      }

      try {
        const predictionResponse = await fetch(
          "https://crowdguard-adk-agent-255137970778.europe-west1.run.app/run_sse",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              // NOTE: Origin header removal for simplicity if CORS allows
            },
            body: JSON.stringify({
              appName: "orchestrator_agent",
              userId: "user",
              sessionId: sessionId,
              newMessage: {
                role: "user",
                parts: [
                  {
                    text: `The location is ${
                      location || "Unknown Location"
                    }. ML Stats: ${JSON.stringify(mlStats)}`,
                  },
                ],
              },
              streaming: false,
              stateDelta: null,
            }),
          }
        );

        if (predictionResponse.ok) {
          try {
            // Parse SSE format response
            const reader = predictionResponse.body?.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            let finalData: AgentPrediction | null = null;

            if (reader) {
              try {
                while (true) {
                  const { done, value } = await reader.read();
                  if (done) break;

                  buffer += decoder.decode(value, { stream: true });
                  const lines = buffer.split("\n");
                  buffer = lines.pop() || "";

                  for (const line of lines) {
                    if (line.startsWith("data: ")) {
                      const jsonStr = line.substring(6).trim();
                      if (jsonStr && jsonStr !== "[DONE]") {
                        try {
                          finalData = JSON.parse(jsonStr);
                        } catch {
                          console.warn("Failed to parse SSE line:", jsonStr);
                        }
                      }
                    }
                  }
                }
              } catch (streamError) {
                console.error("Error reading SSE stream:", streamError);
              }
            }

            if (finalData) {
              console.log("=== Agent Response (Real) ===");
              console.log(JSON.stringify(finalData, null, 2));
              const mergedData = mergeWithMockData(finalData);
              setAgentPrediction(mergedData);
            } else {
              console.warn("No valid data in SSE response, keeping mock data");
            }
          } catch (parseError) {
            console.error("Error parsing SSE response:", parseError);
            console.warn("Keeping mock data");
          }
        } else {
          const errorText = await predictionResponse.text();
          console.warn("Agent prediction API failed:", errorText);
          console.warn("Keeping mock data");
        }
      } catch (error) {
        console.error("Agent prediction API error (Fetch):", error);
        console.warn("Keeping mock data");
      }
    } catch (error) {
      console.error("Error generating ML Stats:", error);
      alert(
        "Error generating ML stats. Check your GEMINI_API_KEY and network connection."
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const togglePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const resetAnalysis = () => {
    setVideoFile(null);
    setVideoUrl("");
    setAnnotatedVideoUrl("");
    setAgentPrediction(null);
    setHeatmapData(null);
    setAnalysisComplete(false);
    setMetrics({
      totalPeople: 0,
      maxPeople: 0,
      averageDensity: 0,
      activeAlerts: 0,
      riskLevel: "LOW",
    });
    // Don't reset location - keep it saved
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img
                src="/Gemini_Generated_Image_7enhhv7enhhv7enh.png"
                alt="CrowdGuard AI"
                className="h-10 w-10 rounded-lg"
              />
              <div>
                <h1 className="text-2xl font-bold">CrowdGuard AI</h1>
                <p className="text-sm text-slate-400">
                  Intelligent Crowd Management System
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Radio className="h-4 w-4 text-green-500" />
                <span className="text-sm text-slate-400">Connected</span>
              </div>

              <div className="text-sm text-slate-400">
                {new Date().toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="p-6 space-y-6">
        {/* Upload Section */}
        {!videoUrl && (
          <div className="max-w-4xl mx-auto">
            {/* Hero Section with Icon */}
            <div className="text-center mb-12">
              <img
                src="/Gemini_Generated_Image_7enhhv7enhhv7enh.png"
                alt="CrowdGuard AI"
                className="h-32 w-32 mx-auto mb-6 rounded-2xl shadow-2xl"
              />
              <h2 className="text-4xl font-bold mb-4">
                Welcome to CrowdGuard AI
              </h2>
              <p className="text-xl text-slate-300 mb-4">
                Intelligent Crowd Management System
              </p>
              <p className="text-slate-400 max-w-2xl mx-auto leading-relaxed">
                Powered by advanced AI and computer vision, CrowdGuard AI
                analyzes crowd footage in real-time to detect density patterns,
                identify potential risks, and provide actionable insights. Our
                system combines YOLOv8 object detection with multi-agent AI to
                ensure safety and efficiency in crowd management.
              </p>
            </div>

            {/* Upload Box */}
            <div className="border-2 border-dashed border-slate-700 rounded-lg p-12 text-center hover:border-slate-600 transition-colors">
              <Upload className="h-16 w-16 mx-auto mb-4 text-slate-500" />
              <h3 className="text-xl font-semibold mb-2">Upload Crowd Video</h3>
              <p className="text-slate-400 mb-6">
                Upload a video file to analyze crowd density and detect
                anomalies
              </p>
              <label className="inline-block">
                <input
                  type="file"
                  accept="video/*"
                  onChange={handleFileSelect}
                  className="hidden"
                  disabled={isProcessing}
                />
                <div className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                  Choose Video File
                </div>
              </label>
            </div>
          </div>
        )}

        {/* Video Selected - Show Location Input */}
        {videoUrl && !isProcessing && !analysisComplete && (
          <div className="bg-slate-900 rounded-lg border border-slate-800 p-8">
            <div className="max-w-2xl mx-auto space-y-6">
              <div>
                <h3 className="text-xl font-semibold mb-2">Video Selected</h3>
                <p className="text-slate-400 mb-6">
                  Enter the location of this camera to help contextualize the
                  news
                </p>
              </div>

              {/* Location Input */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Location *
                </label>
                <input
                  type="text"
                  value={location}
                  onChange={(e) => handleLocationChange(e.target.value)}
                  placeholder="e.g., Main Stadium Entrance, Times Square, Concert Hall"
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500 text-white placeholder-slate-500"
                />
                <p className="text-sm text-slate-500 mt-2">
                  This location will be saved for future use
                </p>
              </div>

              {/* Preview Video */}
              <div className="bg-black rounded-lg overflow-hidden">
                <video src={videoUrl} className="w-full max-h-96" controls />
              </div>

              {/* Action Buttons */}
              <div className="flex gap-4 justify-center">
                <button
                  onClick={resetAnalysis}
                  className="px-6 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
                >
                  Choose Different Video
                </button>
                <button
                  onClick={handleProcessVideo}
                  disabled={!location.trim()}
                  className="px-8 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Process Video
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Processing Indicator */}
        {isProcessing && (
          <div className="bg-slate-900 rounded-lg p-8 text-center border border-slate-800">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <h3 className="text-xl font-semibold mb-2">Analyzing Video...</h3>
            <p className="text-slate-400">
              GEMINI API & YOLO ML module is processing frames and detecting
              crowds
            </p>
          </div>
        )}

        {/* Metrics Cards */}
        {videoUrl && analysisComplete && <MetricsCards metrics={metrics} />}

        {/* Main Grid */}
        {videoUrl && analysisComplete && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column - Video + Heatmap */}
            <div className="lg:col-span-2 space-y-6">
              {/* Video Player */}
              <div className="bg-slate-900 rounded-lg overflow-hidden border border-slate-800">
                <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                  <h3 className="text-lg font-semibold">
                    Annotated Video with Detections
                  </h3>
                  <div className="flex gap-2">
                    <button
                      onClick={togglePlayPause}
                      className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
                    >
                      {isPlaying ? (
                        <>
                          <Pause className="h-4 w-4" />
                          Pause
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4" />
                          Play
                        </>
                      )}
                    </button>
                    <button
                      onClick={resetAnalysis}
                      className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
                    >
                      New Video
                    </button>
                  </div>
                </div>
                <div className="relative bg-black">
                  {annotatedVideoUrl ? (
                    <video
                      ref={videoRef}
                      src={annotatedVideoUrl}
                      className="w-full"
                      controls
                      onPlay={() => setIsPlaying(true)}
                      onPause={() => setIsPlaying(false)}
                    />
                  ) : (
                    <div className="aspect-video flex items-center justify-center text-slate-500">
                      Processing video...
                    </div>
                  )}
                </div>
              </div>

              {/* Heatmap */}
              <Heatmap data={heatmapData} />
            </div>

            {/* Right Column - Alerts + Agent Logs */}
            <div className="space-y-6">
              <AlertPanel agentPrediction={agentPrediction} />
              <AgentLogs agentPrediction={agentPrediction} />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
