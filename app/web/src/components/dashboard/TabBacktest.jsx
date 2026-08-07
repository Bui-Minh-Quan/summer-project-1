import React, { useState, useEffect } from 'react';
import { History, CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react';
import { getClassificationBacktest, getRegressionBacktest } from '../../api/client';

export default function TabBacktest({ symbol }) {
  const [subTab, setSubTab] = useState('classification');
  const [clsData, setClsData] = useState([]);
  const [regData, setRegData] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchBacktestLogs = async () => {
      setLoading(true);
      try {
        if (subTab === 'classification') {
          const res = await getClassificationBacktest(symbol);
          setClsData(res);
        } else {
          const res = await getRegressionBacktest(symbol);
          setRegData(res);
        }
      } catch (err) {
        console.error("Backtest fetch error:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchBacktestLogs();
  }, [symbol, subTab]);

  return (
    <div className="space-y-6">
      {/* Subtab Toggle */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-emerald-400" />
          <h3 className="font-bold text-slate-100">Prediction Audit & Backtest Logs</h3>
        </div>

        <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-semibold">
          <button
            onClick={() => setSubTab('classification')}
            className={`px-4 py-2 rounded-lg transition-all ${subTab === 'classification' ? 'bg-slate-800 text-emerald-400' : 'text-slate-400 hover:text-slate-200'}`}
          >
            vLLM Trend Classification
          </button>
          <button
            onClick={() => setSubTab('regression')}
            className={`px-4 py-2 rounded-lg transition-all ${subTab === 'regression' ? 'bg-slate-800 text-emerald-400' : 'text-slate-400 hover:text-slate-200'}`}
          >
            XGBoost Price Regression
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12 text-slate-400">
          <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
        </div>
      ) : subTab === 'classification' ? (
        /* Classification History Table */
        <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-800/20">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-800/80 text-xs uppercase font-mono text-slate-400 border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Target Date</th>
                <th className="px-4 py-3">Base Price</th>
                <th className="px-4 py-3">Predicted Trend</th>
                <th className="px-4 py-3">Actual Trend</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Model</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {clsData.length === 0 ? (
                <tr>
                  <td colSpan="6" className="text-center py-8 text-slate-500">No classification audit logs recorded for {symbol} yet.</td>
                </tr>
              ) : (
                clsData.map((row, idx) => {
                  const isMatch = row.actual_trend && row.predicted_trend.toLowerCase() === row.actual_trend.toLowerCase();
                  return (
                    <tr key={idx} className="hover:bg-slate-800/40 transition-colors font-mono">
                      <td className="px-4 py-3 text-slate-300">{row.date}</td>
                      <td className="px-4 py-3">{row.price.toFixed(2)} VND</td>
                      <td className="px-4 py-3 font-bold text-emerald-400">{row.predicted_trend}</td>
                      <td className="px-4 py-3 text-slate-300">{row.actual_trend || <span className="text-amber-500/80 italic text-xs">Pending Outcome...</span>}</td>
                      <td className="px-4 py-3">
                        {row.actual_trend ? (
                          isMatch ? (
                            <span className="inline-flex items-center gap-1 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full"><CheckCircle2 className="w-3 h-3" /> Correct</span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 rounded-full"><XCircle className="w-3 h-3" /> Miss</span>
                          )
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs text-amber-400"><Clock className="w-3 h-3" /> Awaiting T+1</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500">{row.model}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      ) : (
        /* Regression History Table */
        <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-800/20">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-800/80 uppercase font-mono text-slate-400 border-b border-slate-800">
              <tr>
                <th className="px-3 py-3">Date</th>
                <th className="px-3 py-3">Price</th>
                <th className="px-3 py-3 text-emerald-400">Pred T+1</th>
                <th className="px-3 py-3">Actual T+1</th>
                <th className="px-3 py-3 text-emerald-400">Pred T+5</th>
                <th className="px-3 py-3">Actual T+5</th>
                <th className="px-3 py-3">Model</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 font-mono">
              {regData.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-8 text-slate-500">No regression audit logs recorded for {symbol} yet.</td>
                </tr>
              ) : (
                regData.map((row, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-3 py-3 text-slate-300">{row.date}</td>
                    <td className="px-3 py-3">{row.price.toFixed(2)}</td>
                    <td className="px-3 py-3 font-bold text-emerald-400">{row.predicted_price_t1.toFixed(2)}</td>
                    <td className="px-3 py-3 text-slate-300">{row.actual_price_t1 ? row.actual_price_t1.toFixed(2) : '---'}</td>
                    <td className="px-3 py-3 font-bold text-emerald-400">{row.predicted_price_t5.toFixed(2)}</td>
                    <td className="px-3 py-3 text-slate-300">{row.actual_price_t5 ? row.actual_price_t5.toFixed(2) : '---'}</td>
                    <td className="px-3 py-3 text-slate-500">{row.model}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}