import React, { useRef, useState } from 'react';
import { UploadCloud, FileText, Loader2, Clock, Share2, CircleDot, Network } from 'lucide-react';

export default function FileUploader({ onUpload, isLoading, graphData }) {
  const fileInputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    setError(null);
    
    if (file) {
      const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
      if (ext !== '.pdf' && ext !== '.txt') {
        setError('Only .pdf and .txt files are supported.');
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleExtract = () => {
    if (selectedFile) {
      onUpload(selectedFile);
    }
  };

  const { metadata, nodes, edges } = graphData || {};

  return (
    <div className="bg-slate-800/40 border border-slate-800 rounded-2xl p-6 h-full flex flex-col justify-between">
      <div>
        <h3 className="text-lg font-bold text-slate-100 mb-2">Upload Document</h3>
        <p className="text-xs text-slate-400 mb-6">Extract temporal financial relationships from raw PDF or TXT reports.</p>

        {/* Dropzone Area */}
        <div 
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
            selectedFile ? 'border-emerald-500/50 bg-emerald-500/5' : 'border-slate-700 hover:border-slate-500 bg-slate-900/50'
          }`}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            fileInputRef.current.files = e.dataTransfer.files;
            handleFileChange({ target: { files: e.dataTransfer.files } });
          }}
        >
          <input 
            type="file" 
            ref={fileInputRef} 
            className="hidden" 
            accept=".pdf,.txt" 
            onChange={handleFileChange}
          />
          
          {selectedFile ? (
            <div className="flex flex-col items-center gap-2">
              <FileText className="w-8 h-8 text-emerald-400" />
              <span className="text-sm font-bold text-slate-200">{selectedFile.name}</span>
              <span className="text-xs text-slate-500">{(selectedFile.size / 1024).toFixed(1)} KB</span>
              <button 
                onClick={() => setSelectedFile(null)}
                className="text-xs text-rose-400 hover:text-rose-300 mt-2"
              >
                Remove
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 cursor-pointer" onClick={() => fileInputRef.current.click()}>
              <UploadCloud className="w-8 h-8 text-slate-500" />
              <span className="text-sm font-bold text-slate-300">Click or drag file here</span>
              <span className="text-xs text-slate-500">Supports .pdf, .txt</span>
            </div>
          )}
        </div>
        {error && <p className="text-rose-400 text-xs mt-2 text-center">{error}</p>}

        {/* Extract Button */}
        <button
          onClick={handleExtract}
          disabled={!selectedFile || isLoading}
          className={`w-full mt-6 py-3 rounded-xl font-bold flex justify-center items-center gap-2 transition-all ${
            !selectedFile || isLoading
              ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
              : 'bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-lg shadow-emerald-500/20 cursor-pointer'
          }`}
        >
          {isLoading ? (
            <><Loader2 className="w-5 h-5 animate-spin" /> Extracting Graph...</>
          ) : (
            <><Network className="w-5 h-5" /> Generate Knowledge Graph</>
          )}
        </button>
      </div>

      {/* Telemetry Badges */}
      {graphData && !isLoading && (
        <div className="mt-8 pt-6 border-t border-slate-800 space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Extraction Telemetry</h4>
          
          <div className="grid grid-cols-1 gap-2">
            <div className="flex items-center justify-between bg-slate-900 px-4 py-2 rounded-lg border border-slate-700/50">
              <span className="flex items-center gap-2 text-xs text-slate-400"><Clock className="w-3.5 h-3.5"/> Latency</span>
              <span className="text-sm font-mono font-bold text-emerald-400">{metadata?.total_latency_seconds?.toFixed(2)}s</span>
            </div>
            
            <div className="flex items-center justify-between bg-slate-900 px-4 py-2 rounded-lg border border-slate-700/50">
              <span className="flex items-center gap-2 text-xs text-slate-400"><CircleDot className="w-3.5 h-3.5"/> Nodes Found</span>
              <span className="text-sm font-mono font-bold text-cyan-400">{nodes?.length || 0}</span>
            </div>

            <div className="flex items-center justify-between bg-slate-900 px-4 py-2 rounded-lg border border-slate-700/50">
              <span className="flex items-center gap-2 text-xs text-slate-400"><Share2 className="w-3.5 h-3.5"/> Edges (Relations)</span>
              <span className="text-sm font-mono font-bold text-purple-400">{edges?.length || 0}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}