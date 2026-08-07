import React from 'react';
import { BrainCircuit, TrendingUp } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

export default function TabInsights({ predictionData }) {
  const { reasoning, confidence, current_price, price_forecasts } = predictionData;

  // Format data for Recharts (combining day 0 current price with day 1-5 forecasts)
  const chartData = [
    { day: 'T+0 (Now)', price: current_price, isActual: true },
    ...(price_forecasts?.map(f => ({
      day: `T+${f.horizon_days}`,
      price: f.expected_price,
      return: f.expected_return_pct,
      isActual: false
    })) || [])
  ];

  // Min/Max for chart Y-axis scaling
  const prices = chartData.map(d => d.price);
  const minPrice = Math.min(...prices) * 0.98;
  const maxPrice = Math.max(...prices) * 1.02;

  // Custom tooltip for Recharts
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-slate-900 border border-slate-700 p-3 rounded-lg shadow-xl">
          <p className="text-slate-300 font-bold mb-1">{label}</p>
          <p className="text-emerald-400 font-mono text-lg">{data.price.toFixed(2)} VND</p>
          {!data.isActual && (
            <p className={`text-xs mt-1 ${data.return >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
              Return: {(data.return * 100).toFixed(2)}%
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      {/* Left Column: TRR Reasoning */}
      <div className="lg:col-span-1 space-y-6">
        <div className="bg-slate-800/40 border border-slate-800 rounded-2xl p-6 h-full flex flex-col">
          <div className="flex items-center gap-2 text-purple-400 mb-4">
            <BrainCircuit className="w-5 h-5" />
            <h3 className="font-bold text-slate-100">vLLM Temporal Relational Reasoning</h3>
          </div>
          
          <div className="flex-1">
            <p className="text-slate-300 leading-relaxed text-sm">
              "{reasoning}"
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-700/50">
            <div className="flex justify-between text-xs font-mono text-slate-400 mb-2">
              <span>Reasoning Confidence</span>
              <span className="text-slate-200">{(confidence * 100).toFixed(1)}%</span>
            </div>
            <div className="h-2 w-full bg-slate-950 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-purple-500 to-indigo-400 rounded-full"
                style={{ width: `${confidence * 100}%` }}
              ></div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Column: XGBoost Horizon Forecast */}
      <div className="lg:col-span-2 space-y-6">
        <div className="bg-slate-800/40 border border-slate-800 rounded-2xl p-6">
          <div className="flex items-center gap-2 text-emerald-400 mb-6">
            <TrendingUp className="w-5 h-5" />
            <h3 className="font-bold text-slate-100">XGBoost 5-Day Horizon Forecast</h3>
          </div>

          {/* Recharts Line Chart */}
          <div className="h-[250px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis 
                  dataKey="day" 
                  stroke="#64748b" 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false}
                />
                <YAxis 
                  domain={[minPrice, maxPrice]} 
                  stroke="#64748b" 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false}
                  tickFormatter={(val) => val.toFixed(1)}
                />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine y={current_price} stroke="#64748b" strokeDasharray="3 3" />
                <Line 
                  type="monotone" 
                  dataKey="price" 
                  stroke="#10b981" 
                  strokeWidth={3} 
                  dot={{ r: 4, fill: '#10b981', strokeWidth: 2, stroke: '#0f172a' }} 
                  activeDot={{ r: 6, fill: '#34d399', stroke: '#0f172a' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Data Table */}
          <div className="mt-6 overflow-hidden rounded-xl border border-slate-700/50 bg-slate-900/50">
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-800/80 text-xs uppercase font-mono text-slate-400">
                <tr>
                  <th className="px-4 py-3">Horizon</th>
                  <th className="px-4 py-3">Expected Price</th>
                  <th className="px-4 py-3 text-right">Predicted Return</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {price_forecasts?.map((f) => (
                  <tr key={f.horizon_days} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3 font-medium text-slate-300">T+{f.horizon_days}</td>
                    <td className="px-4 py-3 font-mono">{f.expected_price.toFixed(2)} VND</td>
                    <td className={`px-4 py-3 font-mono text-right ${f.expected_return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {f.expected_return_pct >= 0 ? '+' : ''}{(f.expected_return_pct * 100).toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

        </div>
      </div>
    </div>
  );
}