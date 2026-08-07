import React, { useState, useEffect } from 'react';
import { Loader2, AlertTriangle } from 'lucide-react';
import { getDualPrediction, getSentimentScore } from '../api/client';
import TickerHeader from '../components/dashboard/TickerHeader';
import TabInsights from '../components/dashboard/TabInsights';
import TabLiveMarket from '../components/dashboard/TabLiveMarket';
import TabBacktest from '../components/dashboard/TabBacktest';
import TabSentiment from '../components/dashboard/TabSentiment';

export default function Dashboard({ selectedSymbol, setSelectedSymbol }) {
  const [activeSubTab, setActiveSubTab] = useState('insights');
  const [predictionData, setPredictionData] = useState(null);
  const [sentimentData, setSentimentData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch initial data when symbol changes
  useEffect(() => {
    const fetchDashboardData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [predRes, sentRes] = await Promise.all([
          getDualPrediction(selectedSymbol),
          getSentimentScore(selectedSymbol)
        ]);
        setPredictionData(predRes);
        setSentimentData(sentRes);
      } catch (err) {
        console.error("Dashboard fetch error:", err);
        setError("Failed to load AI forecasts. Ensure backend services are running.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, [selectedSymbol]);

  const tabs = [
    { id: 'insights', label: 'AI Insights & Forecasts' },
    { id: 'live', label: 'Live Market' },
    { id: 'backtest', label: 'Backtest Audit Logs' },
    { id: 'sentiment', label: 'News & Sentiment' }
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Sticky Header */}
      <TickerHeader 
        selectedSymbol={selectedSymbol} 
        setSelectedSymbol={setSelectedSymbol}
        predictionData={predictionData}
        sentimentData={sentimentData}
      />

      {/* Sub-navigation Tabs */}
      <div className="border-b border-slate-800 bg-slate-900/50 sticky top-[64px] z-40 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-6 overflow-x-auto hide-scrollbar">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveSubTab(tab.id)}
                className={`py-4 px-1 border-b-2 text-sm font-medium whitespace-nowrap transition-colors ${
                  activeSubTab === tab.id 
                    ? 'border-emerald-500 text-emerald-400' 
                    : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-64 text-slate-400">
            <Loader2 className="w-8 h-8 animate-spin text-emerald-500 mb-4" />
            <p className="text-sm font-mono">Running vLLM reasoning & XGBoost regressions...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-64 text-rose-400 bg-rose-500/10 rounded-2xl border border-rose-500/20 p-6">
            <AlertTriangle className="w-8 h-8 mb-2" />
            <p className="text-sm font-mono">{error}</p>
          </div>
        ) : predictionData && sentimentData ? (
          <>
            {activeSubTab === 'insights' && <TabInsights predictionData={predictionData} />}
            {activeSubTab === 'live' && <TabLiveMarket symbol={selectedSymbol} currentPrice={predictionData.current_price} />}
            {activeSubTab === 'backtest' && <TabBacktest symbol={selectedSymbol} />}
            {activeSubTab === 'sentiment' && <TabSentiment symbol={selectedSymbol} sentimentData={sentimentData} />}
          </>
        ) : null}
      </div>
    </div>
  );
}