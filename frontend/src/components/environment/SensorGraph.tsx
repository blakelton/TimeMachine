/**
 * Simple SVG-based line graph for sensor readings
 */

import { useMemo } from "react";
import "./SensorGraph.css";

interface DataPoint {
  timestamp: number;
  value: number;
}

interface SensorGraphProps {
  data: DataPoint[];
  color: string;
  label: string;
  unit: string;
  height?: number;
}

export function SensorGraph({
  data,
  color,
  label,
  unit,
  height = 80,
}: SensorGraphProps) {
  const { path, minValue, maxValue, avgValue } = useMemo(() => {
    if (data.length < 2) {
      return { path: "", minValue: 0, maxValue: 0, avgValue: null };
    }

    // Sort by timestamp
    const sorted = [...data].sort((a, b) => a.timestamp - b.timestamp);

    // Calculate min/max for scaling
    const values = sorted.map((d) => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const avg = values.reduce((sum, v) => sum + v, 0) / values.length;

    // Add padding to range
    const range = max - min || 1;
    const paddedMin = min - range * 0.1;
    const paddedMax = max + range * 0.1;
    const paddedRange = paddedMax - paddedMin;

    // Calculate time range
    const minTime = sorted[0].timestamp;
    const maxTime = sorted[sorted.length - 1].timestamp;
    const timeRange = maxTime - minTime || 1;

    // SVG dimensions (aspect ratio ~4:1)
    const width = 300;
    const svgHeight = height;
    const padding = { top: 5, right: 5, bottom: 5, left: 5 };
    const graphWidth = width - padding.left - padding.right;
    const graphHeight = svgHeight - padding.top - padding.bottom;

    // Generate path
    const points = sorted.map((d, i) => {
      const x = padding.left + ((d.timestamp - minTime) / timeRange) * graphWidth;
      const y =
        padding.top +
        graphHeight -
        ((d.value - paddedMin) / paddedRange) * graphHeight;
      return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    });

    return {
      path: points.join(" "),
      minValue: min,
      maxValue: max,
      avgValue: avg,
    };
  }, [data, height]);

  if (data.length < 2) {
    return null;
  }

  return (
    <div className="sensor-graph">
      <div className="graph-header">
        <span className="graph-label" style={{ color }}>
          {label}
        </span>
        <div className="graph-stats">
          <span className="stat">
            <span className="stat-label">Min:</span>
            <span className="stat-value">{minValue.toFixed(1)}{unit}</span>
          </span>
          <span className="stat">
            <span className="stat-label">Avg:</span>
            <span className="stat-value">{avgValue?.toFixed(1)}{unit}</span>
          </span>
          <span className="stat">
            <span className="stat-label">Max:</span>
            <span className="stat-value">{maxValue.toFixed(1)}{unit}</span>
          </span>
        </div>
      </div>
      <svg
        viewBox={`0 0 300 ${height}`}
        className="graph-svg"
        preserveAspectRatio="none"
      >
        {/* Grid lines */}
        <line
          x1="5"
          y1={height / 2}
          x2="295"
          y2={height / 2}
          stroke="var(--color-border-light)"
          strokeWidth="1"
          strokeDasharray="4"
        />

        {/* Data line */}
        <path
          d={path}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Area fill */}
        <path
          d={`${path} L 295 ${height - 5} L 5 ${height - 5} Z`}
          fill={color}
          fillOpacity="0.1"
        />
      </svg>
    </div>
  );
}
