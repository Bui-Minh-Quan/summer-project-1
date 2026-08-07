import React, { useState, useEffect } from 'react';
import { TrendingUp, Home, LayoutDashboard, Network, Activity } from 'lucide-react';
import apiClient from '../../api/client';

export default function Navbar({ activeTab, setActiveTab }) {
  const [isSystemOnline, setIsSystemOnline] = useState(false);

  useEffect(() => {
    const checkSystemStatus = async () => {
      try {
        const response = await apiClient.get('/stream/status');
        if (response.data && response.data.status) {
          setIsSystemOnline(true);
        }
      } catch (err) {
        setIsSystemOnline(false);
      }
    };

    checkSystemStatus();
    const interval = setInterval(checkSystemStatus, 15000); // Poll status every 15s
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { id: 'home', label: 'Home', icon: Home },
    { id: 'dashboard', label: 'Stock Dashboard', icon: LayoutDashboard },
    { id: 'extractor', label: 'Graph Extractor', icon: Network },
  ];

  return (
    <header className="sticky top-0 z-50 bg-slate-900/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Platform Branding */}
          <div 
            className="flex items-center gap-3 cursor-pointer"
            onClick={() => setActiveTab('home')}
          >
            <div className="p-2 bg-emerald-500/10 rounded-xl border border-emerald-500/20 text-emerald-400">
              <TrendingUp className="w-6 h-6" />
            </div>
            <div>
              <span className="text-lg font-bold bg-gradient-to-r from-emerald-400 to-teal-200 bg-clip-text text-transparent">
                Financial AI
              </span>
              <span className="text-xs block text-slate-400 font-mono">VN30 Quant Platform</span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center gap-1 bg-slate-950/50 p-1.5 rounded-xl border border-slate-800/80">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? 'bg-slate-800 text-emerald-400 shadow-sm border border-slate-700/50'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* System Status Indicator */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-950/60 border border-slate-800 text-xs font-mono">
            <span className={`relative flex h-2 w-2`}>
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isSystemOnline ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
              <span className={`relative inline-flex rounded-full h-2 w-2 ${isSystemOnline ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
            </span>
            <span className={isSystemOnline ? 'text-emerald-400' : 'text-rose-400'}>
              {isSystemOnline ? 'API Gateway Live' : 'API Offline'}
            </span>
          </div>

        </div>
      </div>
    </header>
  );
}