'use client';

import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

export interface ChartPoint {
  date:      string; // formatted date string for display
  predicted: number;
  actual:    number | null;
}

interface PredictionsChartProps {
  data: ChartPoint[];
}

export function PredictionsChart({ data }: PredictionsChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
        No prediction data available yet.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: '#94a3b8' }}
          tickLine={false}
          axisLine={{ stroke: '#e2e8f0' }}
          interval="preserveStartEnd"
        />
        <YAxis
          domain={[0, 1]}
          tickFormatter={v => `${Math.round(v * 100)}%`}
          tick={{ fontSize: 11, fill: '#94a3b8' }}
          tickLine={false}
          axisLine={false}
          width={44}
        />
        <Tooltip
          formatter={(value: number) => [`${(value * 100).toFixed(1)}%`]}
          contentStyle={{ fontSize: 12, borderRadius: '8px', border: '1px solid #e2e8f0' }}
        />
        <Legend
          wrapperStyle={{ fontSize: 12 }}
          formatter={v => v === 'predicted' ? 'Predicted score' : 'Actual virality score'}
        />
        <Line
          type="monotone"
          dataKey="predicted"
          stroke="#AD2D37"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
        <Line
          type="monotone"
          dataKey="actual"
          stroke="#1E3A5F"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
          connectNulls={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
