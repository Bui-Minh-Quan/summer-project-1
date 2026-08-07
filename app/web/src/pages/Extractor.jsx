import React, { useState } from 'react';
import { extractKnowledgeGraph } from '../api/client';
import FileUploader from '../components/graph/FileUploader';
import GraphCanvas from '../components/graph/GraphCanvas';

export default function Extractor() {
  const [isLoading, setIsLoading] = useState(false);
  const [graphData, setGraphData] = useState(null);
  const [error, setError] = useState(null);

  const handleUploadAndExtract = async (file) => {
    setIsLoading(true);
    setError(null);
    try {
      // POST to /api/v1/graph/extract
      const data = await extractKnowledgeGraph(file);
      setGraphData(data);
    } catch (err) {
      console.error("Graph extraction failed:", err);
      setError(err.response?.data?.detail || "Extraction failed. Ensure vLLM engine is running.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-[calc(100vh-130px)]">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-100">Knowledge Graph Extractor</h2>
        <p className="text-slate-400 text-sm mt-1">Upload a financial report (PDF/TXT) to construct relationship graphs via vLLM.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[600px]">
        {/* Left Panel: File Control */}
        <div className="lg:col-span-1 h-full">
          <FileUploader 
            onUpload={handleUploadAndExtract} 
            isLoading={isLoading} 
            graphData={graphData} 
          />
          {error && (
            <div className="mt-4 p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl">
              {error}
            </div>
          )}
        </div>

        {/* Right Panel: Interactive Canvas */}
        <div className="lg:col-span-3 h-full">
          <GraphCanvas graphData={graphData} />
        </div>
      </div>
    </div>
  );
}