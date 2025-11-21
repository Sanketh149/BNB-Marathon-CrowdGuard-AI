import { useEffect, useRef } from "react";
import { Flame } from "lucide-react";

interface HeatmapProps {
  data: {
    points: [number, number][];
    width: number;
    height: number;
  } | null;
}

export default function Heatmap({ data }: HeatmapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!data || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Set canvas size
    canvas.width = data.width;
    canvas.height = data.height;

    // Clear canvas
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw heatmap
    const gradient = ctx.createRadialGradient(0, 0, 0, 0, 0, 50);
    gradient.addColorStop(0, "rgba(255, 0, 0, 0.8)");
    gradient.addColorStop(0.5, "rgba(255, 165, 0, 0.4)");
    gradient.addColorStop(1, "rgba(255, 255, 0, 0)");

    data.points.forEach(([x, y]) => {
      ctx.save();
      ctx.translate(x, y);
      ctx.fillStyle = gradient;
      ctx.fillRect(-50, -50, 100, 100);
      ctx.restore();
    });

    // Apply blur effect
    ctx.filter = "blur(10px)";
    ctx.drawImage(canvas, 0, 0);
    ctx.filter = "none";
  }, [data]);

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Flame className="h-5 w-5 text-orange-500" />
          Density Heatmap
        </h3>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-green-500 rounded"></div>
            <span className="text-slate-400">Low</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-yellow-500 rounded"></div>
            <span className="text-slate-400">Medium</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-red-500 rounded"></div>
            <span className="text-slate-400">High</span>
          </div>
        </div>
      </div>

      <div className="relative bg-slate-950 flex items-center justify-center p-4">
        {!data ? (
          <div className="text-center text-slate-500 py-12">
            <Flame className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No heatmap data</p>
            <p className="text-sm">Upload a video to generate heatmap</p>
          </div>
        ) : (
          <canvas
            ref={canvasRef}
            className="max-w-full max-h-[400px] border border-slate-800 rounded"
          />
        )}
      </div>
    </div>
  );
}
