import React, { useState } from 'react';
import { 
  BrainCircuit, 
  TrendingUp, 
  Search, 
  ArrowUpRight, 
  Zap, 
  Network, 
  Database,
  BarChart3,
  Sparkles
} from 'lucide-react';

// VN30 Equities with Primary Display Names
const VN30_PORTFOLIO = [
  { symbol: 'ACB', name: 'Ngân hàng Á Châu', category: 'Banking' },
  { symbol: 'BID', name: 'Ngân hàng BIDV', category: 'Banking' },
  { symbol: 'CTG', name: 'Ngân hàng VietinBank', category: 'Banking' },
  { symbol: 'DGC', name: 'Hóa chất Đức Giang', category: 'Materials' },
  { symbol: 'FPT', name: 'Tập đoàn FPT', category: 'Technology' },
  { symbol: 'GAS', name: 'Tổng Công ty Khí VN', category: 'Energy' },
  { symbol: 'GVR', name: 'Tập đoàn Cao su VN', category: 'Industrials' },
  { symbol: 'HPG', name: 'Tập đoàn Hòa Phát', category: 'Materials' },
  { symbol: 'LPB', name: 'Ngân hàng LPBank', category: 'Banking' },
  { symbol: 'MBB', name: 'Ngân hàng Quân Đội (MB)', category: 'Banking' },
  { symbol: 'MSN', name: 'Tập đoàn Masan', category: 'Consumer' },
  { symbol: 'MWG', name: 'Thế Giới Di Động', category: 'Retail' },
  { symbol: 'PLX', name: 'Petrolimex', category: 'Energy' },
  { symbol: 'SAB', name: 'Sabeco', category: 'Consumer' },
  { symbol: 'SHB', name: 'Ngân hàng SHB', category: 'Banking' },
  { symbol: 'SSB', name: 'Ngân hàng SeABank', category: 'Banking' },
  { symbol: 'SSI', name: 'Chứng khoán SSI', category: 'Financials' },
  { symbol: 'STB', name: 'Ngân hàng Sacombank', category: 'Banking' },
  { symbol: 'TCB', name: 'Ngân hàng Techcombank', category: 'Banking' },
  { symbol: 'TPB', name: 'Ngân hàng TPBank', category: 'Banking' },
  { symbol: 'VCB', name: 'Ngân hàng Vietcombank', category: 'Banking' },
  { symbol: 'VHM', name: 'Vinhomes', category: 'Real Estate' },
  { symbol: 'VIB', name: 'Ngân hàng VIB', category: 'Banking' },
  { symbol: 'VIC', name: 'Tập đoàn Vingroup', category: 'Real Estate' },
  { symbol: 'VJC', name: 'Vietjet Air', category: 'Aviation' },
  { symbol: 'VNM', name: 'Vinamilk', category: 'Consumer' },
  { symbol: 'VPB', name: 'Ngân hàng VPBank', category: 'Banking' },
  { symbol: 'VPL', name: 'Tập đoàn Vinpearl', category: 'Hospitality' },
  { symbol: 'VRE', name: 'Vincom Retail', category: 'Real Estate' },
];

export default function Home({ onNavigate, onSelectSymbol }) {
  const [searchTerm, setSearchTerm] = useState('');

  // Filter tickers based on search query
  const filteredPortfolio = VN30_PORTFOLIO.filter(
    (item) =>
      item.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.category.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-16">
      
      {/* HERO SECTION */}
      <section className="text-center space-y-6 pt-6">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Next-Gen VN30 AI Quantitative Engine</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-black tracking-tight text-slate-100">
          VN30 Financial <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">AI Engine</span>
        </h1>

        <p className="max-w-3xl mx-auto text-slate-400 text-base sm:text-lg leading-relaxed">
          Dual-Model Quantitative Intelligence combining <strong className="text-slate-200">vLLM Temporal Relational Reasoning</strong> with <strong className="text-slate-200">XGBoost Multi-Horizon Forecasting</strong> for Vietnamese equity markets.
        </p>

        <div className="flex flex-col sm:flex-row justify-center items-center gap-4 pt-2">
          <button
            onClick={() => onNavigate('dashboard')}
            className="w-full sm:w-auto px-7 py-3.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-xl shadow-lg shadow-emerald-500/20 transition-all flex items-center justify-center gap-2"
          >
            <TrendingUp className="w-5 h-5" />
            Launch Stock Dashboard
          </button>
          <button
            onClick={() => onNavigate('extractor')}
            className="w-full sm:w-auto px-7 py-3.5 bg-slate-800/80 hover:bg-slate-700 text-slate-200 font-semibold rounded-xl border border-slate-700/80 transition-all flex items-center justify-center gap-2"
          >
            <Network className="w-5 h-5 text-teal-400" />
            Extract Knowledge Graph
          </button>
        </div>
      </section>

      {/* SYSTEM ARCHITECTURE CARDS */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1 */}
        <div className="bg-slate-800/40 border border-slate-800 p-6 rounded-2xl hover:border-slate-700 transition-all space-y-3">
          <div className="p-3 bg-purple-500/10 border border-purple-500/20 text-purple-400 rounded-xl w-fit">
            <BrainCircuit className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-slate-100">vLLM Reasoning Engine</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Extracts temporal subgraphs from Neo4j, applies exponential time decay, and generates chain-of-thought directional trend justifications.
          </p>
        </div>

        {/* Card 2 */}
        <div className="bg-slate-800/40 border border-slate-800 p-6 rounded-2xl hover:border-slate-700 transition-all space-y-3">
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl w-fit">
            <BarChart3 className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-slate-100">Multi-Horizon XGBoost</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Independent classifiers and regressors predicting daily price target returns across 1 to 5 trading day horizons ($t+1 \dots t+5$).
          </p>
        </div>

        {/* Card 3 */}
        <div className="bg-slate-800/40 border border-slate-800 p-6 rounded-2xl hover:border-slate-700 transition-all space-y-3">
          <div className="p-3 bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 rounded-xl w-fit">
            <Zap className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-slate-100">Real-Time Event Pipelines</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Kafka streaming for live OHLCV quotes and FireAnt social media feeds continuously quantifying market sentiment and retail hype.
          </p>
        </div>
      </section>

      {/* VN30 LAUNCH GRID */}
      <section className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              <Database className="w-5 h-5 text-emerald-400" />
              VN30 Equity Universe
            </h2>
            <p className="text-xs text-slate-400 mt-1">Select any stock to inspect AI forecasts, social hype, and backtest audit logs.</p>
          </div>

          {/* Search Input */}
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search symbol or name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-slate-950/80 border border-slate-800 text-xs rounded-xl pl-9 pr-4 py-2.5 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50 transition-all"
            />
          </div>
        </div>

        {/* Grid Cards */}
        {filteredPortfolio.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-sm">
            No stock ticker found matching "{searchTerm}"
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-6 gap-3.5">
            {filteredPortfolio.map((stock) => (
              <button
                key={stock.symbol}
                onClick={() => onSelectSymbol(stock.symbol)}
                className="group relative bg-slate-800/40 hover:bg-slate-800 border border-slate-800 hover:border-emerald-500/40 p-4 rounded-xl transition-all duration-200 text-left flex flex-col justify-between h-28"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-base text-slate-100 group-hover:text-emerald-400 transition-colors">
                      {stock.symbol}
                    </span>
                    <ArrowUpRight className="w-4 h-4 text-slate-600 group-hover:text-emerald-400 transition-colors" />
                  </div>
                  <span className="text-[11px] text-slate-400 font-medium line-clamp-1 mt-1">
                    {stock.name}
                  </span>
                </div>

                <div className="mt-2">
                  <span className="inline-block px-2 py-0.5 rounded bg-slate-900/80 text-[10px] font-mono text-slate-500 border border-slate-800/80">
                    {stock.category}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

    </div>
  );
}