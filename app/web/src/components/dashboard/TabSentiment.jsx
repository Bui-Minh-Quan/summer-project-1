import React, { useState, useEffect } from 'react';
import { Flame, Newspaper, ThumbsUp, MessageSquare, Share2, ExternalLink, X, Loader2 } from 'lucide-react';
import { getRelatedNews } from '../../api/client';

export default function TabSentiment({ symbol, sentimentData }) {
  const [news, setNews] = useState([]);
  const [loadingNews, setLoadingNews] = useState(false);
  const [selectedArticle, setSelectedArticle] = useState(null);

  useEffect(() => {
    const fetchNews = async () => {
      setLoadingNews(true);
      try {
        const docs = await getRelatedNews(symbol);
        setNews(docs);
      } catch (err) {
        console.error("News fetch error:", err);
      } finally {
        setLoadingNews(false);
      }
    };

    fetchNews();
  }, [symbol]);

  const { positive_count, negative_count, neutral_count, total_engagement, normalized_hype_score } = sentimentData || {};

  return (
    <div className="space-y-8">
      {/* Sentiment Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-800/40 border border-slate-800 p-5 rounded-2xl flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block mb-1">Positive Sentiment</span>
            <span className="text-2xl font-bold font-mono text-emerald-400">{positive_count || 0}</span>
            <span className="text-xs text-slate-400 block mt-0.5">Posts tagged positive</span>
          </div>
          <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-xl border border-emerald-500/20">
            <ThumbsUp className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-slate-800/40 border border-slate-800 p-5 rounded-2xl flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block mb-1">Negative Sentiment</span>
            <span className="text-2xl font-bold font-mono text-rose-400">{negative_count || 0}</span>
            <span className="text-xs text-slate-400 block mt-0.5">Posts tagged negative</span>
          </div>
          <div className="p-3 bg-rose-500/10 text-rose-400 rounded-xl border border-rose-500/20">
            <MessageSquare className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-slate-800/40 border border-slate-800 p-5 rounded-2xl flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block mb-1">Total Engagement</span>
            <span className="text-2xl font-bold font-mono text-cyan-400">{(total_engagement || 0).toLocaleString()}</span>
            <span className="text-xs text-slate-400 block mt-0.5">Likes, replies & shares</span>
          </div>
          <div className="p-3 bg-cyan-500/10 text-cyan-400 rounded-xl border border-cyan-500/20">
            <Share2 className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-slate-800/40 border border-slate-800 p-5 rounded-2xl flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block mb-1">Hype Index</span>
            <span className="text-2xl font-bold font-mono text-indigo-400">{normalized_hype_score ? normalized_hype_score.toFixed(2) : "0.00"}</span>
            <span className="text-xs text-slate-400 block mt-0.5">Normalized ratio</span>
          </div>
          <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
            <Flame className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Related News List */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-slate-100">
          <Newspaper className="w-5 h-5 text-emerald-400" />
          <h3 className="font-bold text-lg">Related Market News ({symbol})</h3>
        </div>

        {loadingNews ? (
          <div className="flex justify-center py-12 text-slate-400">
            <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
          </div>
        ) : news.length === 0 ? (
          <div className="text-center py-12 text-slate-500 bg-slate-800/20 rounded-2xl border border-slate-800">
            No related news articles found for {symbol}.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {news.map((item) => (
              <div 
                key={item.id}
                onClick={() => setSelectedArticle(item)}
                className="bg-slate-800/30 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 p-5 rounded-2xl transition-all cursor-pointer flex flex-col justify-between space-y-3 group"
              >
                <div>
                  <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
                    <span className="bg-slate-900 border border-slate-700 px-2.5 py-0.5 rounded-full text-emerald-400">{item.source}</span>
                    <span>{new Date(item.published_at).toLocaleDateString()}</span>
                  </div>
                  <h4 className="font-bold text-slate-100 group-hover:text-emerald-400 transition-colors line-clamp-2">
                    {item.title}
                  </h4>
                  <p className="text-xs text-slate-400 line-clamp-3 mt-2 leading-relaxed">
                    {item.content}
                  </p>
                </div>
                <div className="text-xs text-emerald-400 font-semibold flex items-center gap-1 pt-2">
                  Read article snippet <ExternalLink className="w-3.5 h-3.5" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Article Content Preview Modal */}
      {selectedArticle && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl relative">
            <button 
              onClick={() => setSelectedArticle(null)}
              className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-100 bg-slate-800 rounded-xl border border-slate-700 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
              <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full">{selectedArticle.source}</span>
              <span>{new Date(selectedArticle.published_at).toLocaleString()}</span>
            </div>

            <h3 className="text-xl font-bold text-slate-100 pr-8">{selectedArticle.title}</h3>
            
            <div className="text-sm text-slate-300 leading-relaxed max-h-[300px] overflow-y-auto pr-2 bg-slate-950/50 p-4 rounded-xl border border-slate-800">
              {selectedArticle.content}
            </div>

            {selectedArticle.url && (
              <a 
                href={selectedArticle.url} 
                target="_blank" 
                rel="noreferrer"
                className="inline-flex items-center gap-2 text-xs font-bold text-emerald-400 hover:underline pt-2"
              >
                Open Original Source Article <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}