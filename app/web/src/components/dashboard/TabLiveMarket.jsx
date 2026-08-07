import React, { useState, useEffect } from 'react';
import { Activity, BarChart2, Radio, Loader2 } from 'lucide-react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useMarketStream } from '../../api/websocket';
import { getMarketHistory } from '../../api/client';

export default function TabLiveMarket({ symbol, currentPrice }) {
  const { latestTick, isConnected } = useMarketStream(symbol);
  const [ticks, setTicks] = useState([]);
  const [loadingHistory, setLoadingNews] = useState(true);

  // 1. Fetch initial historical OHLCV bars from MongoDB on symbol change
  useEffect(() => {
    const fetchHistory = async () => {
      setLoadingNews(true);
      try {
        const history = await getMarketHistory(symbol, 30);
        if (history && history.length > 0) {
          setTicks(history);
        } else {
          // Fallback if DB has no historical quotes yet
          setTicks([
            { time: 'T-0', close: currentPrice || 10.0, open: currentPrice || 10.0, high: currentPrice || 10.0, low: currentPrice || 10.0, volume: 1000 }
          ]);
        }
      } catch (err) {
        console.error("Failed to fetch market history:", err);
      } finally {
        setLoadingNews(false);
      }
    };

    fetchHistory();
  }, [symbol, currentPrice]);

  // 2. Append new live ticks incoming from Kafka WebSocket
  useEffect(() => {
    if (latestTick) {
      const timeStr = new Date().toLocaleTimeString();
      const formattedTick = {
        time: timeStr,
        close: latestTick.close,
        open: latestTick.open,
        high: latestTick.high,
        low: latestTick.low,
        volume: latestTick.volume
      };

      setTicks((prev) => {
        // Prevent duplicate ticks or append
        const updated = [...prev, formattedTick];
        return updated.slice(-40); // Keep last 40 data points
      });
    }
  }, [latestTick]);

  const lastTick = ticks[ticks.length - 1];

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

      {loadingHistory ? (
        <div className="flex justify-center py-16 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin text-emerald-500 mb-2" />
        </div>
      ) : (
        <>
          {/* Price Action Area Chart */}
          <div className="bg-slate-800/40 border border-slate-800 p-6 rounded-2xl space-y-4">
            <div className="flex items-center gap-2 text-emerald-400">
              <Activity className="w-5 h-5" />
              <h3 className="font-bold text-slate-100">Price Action History & Stream</h3>
            </div>

            <div className="h-[260px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={ticks}>
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
                <BarChart data={ticks}>
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
        </>
      )}
    </div>
  );
}