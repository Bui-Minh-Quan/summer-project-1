import React from 'react';
import { Activity, Flame, ChevronDown } from 'lucide-react';
import { useMarketStream } from '../../api/websocket';

const VN30_SYMBOLS = [
  "ACB", "BID", "CTG", "DGC", "FPT", "GAS", "GVR", "HPG", "LPB", 
  "MBB", "MSN", "MWG", "PLX", "SAB", "SHB", "SSB", "SSI", "STB", "TCB", 
  "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VPL", "VRE"
];

export default function TickerHeader({ selectedSymbol, setSelectedSymbol, predictionData, sentimentData }) {
  // Connect to live Kafka market stream via WebSocket
  const { latestTick, isConnected } = useMarketStream(selectedSymbol);

  // Use live price if available, otherwise fallback to the DB base price
  const displayPrice = latestTick?.close || predictionData?.current_price || 0.0;
  
  const trend = predictionData?.trend || "Sideways";
  const confidence = predictionData?.confidence || 0;
  const hypeScore = sentimentData?.normalized_hype_score || 0;

  // Dynamic styling based on trend
  const trendColors = {
    Bullish: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    Bearish: "bg-rose-500/10 text-rose-400 border-rose-500/20",
    Sideways: "bg-slate-500/10 text-slate-400 border-slate-500/20"
  };

  return (
    <div className="bg-slate-900 border-b border-slate-800 pt-6 pb-4">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
        
        {/* Left: Ticker Selector & Price */}
        <div className="flex items-end gap-6">
          <div className="relative">
            <label className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-1 block">Selected Ticker</label>
            <div className="relative">
              <select
                value={selectedSymbol}
                onChange={(e) => setSelectedSymbol(e.target.value)}
                className="appearance-none bg-slate-950 border border-slate-700 text-slate-100 text-2xl font-black rounded-xl pl-4 pr-10 py-2 focus:outline-none focus:border-emerald-500 transition-colors cursor-pointer"
              >
                {VN30_SYMBOLS.map(sym => (
                  <option key={sym} value={sym}>{sym}</option>
                ))}
              </select>
              <ChevronDown className="w-5 h-5 text-slate-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>

          <div>
            <label className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-1 block">
              Current Price {isConnected && <span className="text-emerald-500 ml-1">● Live</span>}
            </label>
            <div className="text-3xl font-mono text-slate-100 flex items-baseline gap-1">
              {displayPrice > 0 ? displayPrice.toFixed(2) : "---"}
              <span className="text-sm text-slate-500 mb-1">VND</span>
            </div>
          </div>
        </div>

        {/* Right: Quick Metric Badges */}
        <div className="flex gap-3">
          {/* AI Trend Badge */}
          <div className={`flex flex-col justify-center px-4 py-2 rounded-xl border ${trendColors[trend]}`}>
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider mb-0.5">
              <Activity className="w-3.5 h-3.5" />
              vLLM AI Trend
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-lg font-bold">{trend}</span>
              <span className="text-xs opacity-75">{(confidence * 100).toFixed(0)}% conf</span>
            </div>
          </div>

          {/* Social Sentiment Badge */}
          <div className="flex flex-col justify-center px-4 py-2 rounded-xl border bg-indigo-500/10 text-indigo-400 border-indigo-500/20">
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider mb-0.5">
              <Flame className="w-3.5 h-3.5" />
              Social Hype Score
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-lg font-bold">{hypeScore > 0 ? '+' : ''}{hypeScore.toFixed(2)}</span>
              <span className="text-xs opacity-75">(-1.0 to 1.0)</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}