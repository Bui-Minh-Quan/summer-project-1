import React, { useState, useEffect } from 'react';
import { Activity, BarChart2, Radio } from 'lucide-react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useMarketStream } from '../../api/websocket';

export default function TabLiveMarket({ symbol, currentPrice }) {
  const { latestTick, isConnected } = useMarketStream(symbol);
  const [ticks, setTicks] = useState([]);

  // Accumulate incoming live ticks from WebSocket
  useEffect(() => {
    if (latestTick) {
      const timeStr = new Date().toLocaleTimeString();
      setTicks((prev) => {
        const nextTicks = [...prev, { ...latestTick, time: timeStr }];
        return nextTicks.slice(-30); // Keep last 30 live ticks
      });
    }
  }, [latestTick]);

  // Fallback initial data if streaming hasn't pushed ticks yet
  const displayTicks = ticks.length > 0 ? ticks : [
    { time: 'Initial', close: currentPrice || 10.0, open: currentPrice || 10.0, high: currentPrice || 10.0, low: currentPrice || 10.0, volume: 1000 }
  ];

  const lastTick = displayTicks[displayTicks.length - 1];

  return (
    <div className="space-y-6">
      {/* Live Metrics Header */}
      <div className="bg-slate-800/40 border border-slate-800 p-4 rounded-2xl flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-xl border ${isConnected ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'}`}>
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h4 className="font-bold text-slate-100 flex items-center gap-2">
              Live Kafka Stream: {symbol}
              <span className={`text-xs font-mono px-2 py-0.5 rounded-full ${isConnected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}`}>
                {isConnected ? 'Active' : 'Connecting...'}
              </span>
            </h4>
            <p className="text-xs text-slate-400">Receiving real-time OHLCV ticks from <code className="text-slate-300 font-mono">market-ohlcv</code> topic</p>
          </div>
        </div>

        <div className="flex gap-6 font-mono text-xs">
          <div>
            <span className="text-slate-500 block">LAST CLOSE</span>
            <span className="text-slate-100 font-bold text-sm">{lastTick?.close?.toFixed(2) || '---'} VND</span>
          </div>
          <div>
            <span className="text-slate-500 block">HIGH</span>
            <span className="text-emerald-400 font-bold text-sm">{lastTick?.high?.toFixed(2) || '---'}</span>
          </div>
          <div>
            <span className="text-slate-500 block">LOW</span>
            <span className="text-rose-400 font-bold text-sm">{lastTick?.low?.toFixed(2) || '---'}</span>
          </div>
          <div>
            <span className="text-slate-500 block">VOLUME</span>
            <span className="text-cyan-400 font-bold text-sm">{lastTick?.volume?.toLocaleString() || '---'}</span>
          </div>
        </div>
      </div>

      {/* Price Action Area Chart */}
      <div className="bg-slate-800/40 border border-slate-800 p-6 rounded-2xl space-y-4">
        <div className="flex items-center gap-2 text-emerald-400">
          <Activity className="w-5 h-5" />
          <h3 className="font-bold text-slate-100">Live Price Action (Close Price)</h3>
        </div>

        <div className="h-[260px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={displayTicks}>
              <defs>
                <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
              <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} domain={['auto', 'auto']} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                itemStyle={{ color: '#34d399' }}
              />
              <Area type="monotone" dataKey="close" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#priceGradient)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Volume Chart */}
      <div className="bg-slate-800/40 border border-slate-800 p-6 rounded-2xl space-y-4">
        <div className="flex items-center gap-2 text-cyan-400">
          <BarChart2 className="w-5 h-5" />
          <h3 className="font-bold text-slate-100">Trading Volume</h3>
        </div>

        <div className="h-[160px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={displayTicks}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
              <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                itemStyle={{ color: '#22d3ee' }}
              />
              <Bar dataKey="volume" fill="#06b6d4" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}