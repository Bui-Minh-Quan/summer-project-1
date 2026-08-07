import React, { useState } from 'react';
import Navbar from './components/common/Navbar';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import Extractor from './pages/Extractor';

export default function App() {
  const [activeTab, setActiveTab] = useState('home');
  const [selectedSymbol, setSelectedSymbol] = useState('FPT');

  const handleSelectSymbol = (symbol) => {
    setSelectedSymbol(symbol);
    setActiveTab('dashboard');
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard selectedSymbol={selectedSymbol} setSelectedSymbol={setSelectedSymbol} />;
      case 'extractor':
        return <Extractor />;
      case 'home':
      default:
        return <Home onNavigate={setActiveTab} onSelectSymbol={handleSelectSymbol} />;
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="flex-1">
        {renderContent()}
      </main>
      <footer className="border-t border-slate-800/80 py-6 text-center text-xs text-slate-500 font-mono">
        Financial AI Platform &copy; 2026 — VN30 Quantitative Engine
      </footer>
    </div>
  );
}