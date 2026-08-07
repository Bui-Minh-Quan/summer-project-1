import React, { useCallback, useMemo, useState, useEffect } from 'react';
import { ReactFlow, Controls, Background, MarkerType, useNodesState, useEdgesState, Panel } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { toPng, toSvg } from 'html-to-image';
import { Download, Image as ImageIcon, Info } from 'lucide-react';

// Custom Node Component to apply colored styling based on Entity Type
const CustomNode = ({ data }) => {
  const typeColors = {
    STOCK: "bg-emerald-500/20 border-emerald-500 text-emerald-400",
    ORGANIZATION: "bg-blue-500/20 border-blue-500 text-blue-400",
    SECTOR: "bg-cyan-500/20 border-cyan-500 text-cyan-400",
    COMMODITY: "bg-amber-500/20 border-amber-500 text-amber-400",
    PERSON: "bg-purple-500/20 border-purple-500 text-purple-400",
    INDEX: "bg-rose-500/20 border-rose-500 text-rose-400",
    OTHER: "bg-slate-500/20 border-slate-500 text-slate-300",
  };
  
  const colorClass = typeColors[data.type] || typeColors.OTHER;

  return (
    <div className={`px-4 py-2 shadow-lg rounded-lg border-2 backdrop-blur-md min-w-[120px] text-center ${colorClass}`}>
      <div className="text-[9px] uppercase tracking-widest opacity-80 mb-1">{data.type}</div>
      <div className="font-bold text-sm">{data.label}</div>
    </div>
  );
};

const nodeTypes = { custom: CustomNode };

export default function GraphCanvas({ graphData }) {
  const [selectedEdge, setSelectedEdge] = useState(null);

  // Generate layout nodes and edges from API payload
  const { initialNodes, initialEdges } = useMemo(() => {
    if (!graphData || !graphData.nodes) return { initialNodes: [], initialEdges: [] };

    const radius = Math.max(250, graphData.nodes.length * 25);
    const centerX = 400;
    const centerY = 300;

    const nodes = graphData.nodes.map((n, index) => {
      // Circular layout
      const angle = (index / graphData.nodes.length) * 2 * Math.PI;
      return {
        id: n.id,
        type: 'custom',
        position: {
          x: centerX + radius * Math.cos(angle),
          y: centerY + radius * Math.sin(angle),
        },
        data: { label: n.label, type: n.type },
      };
    });

    const edges = graphData.edges.map((e, index) => {
      const color = e.impact === 'POSITIVE' ? '#10b981' : e.impact === 'NEGATIVE' ? '#f43f5e' : '#64748b';
      return {
        id: `e-${index}`,
        source: e.source,
        target: e.target,
        label: e.label,
        animated: true,
        style: { stroke: color, strokeWidth: 2 },
        labelStyle: { fill: '#cbd5e1', fontWeight: 600, fontSize: 12 },
        labelBgStyle: { fill: '#0f172a', stroke: '#334155', strokeWidth: 1 },
        markerEnd: { type: MarkerType.ArrowClosed, color: color },
        data: { reasoning: e.reasoning, confidence: e.confidence, impact: e.impact },
      };
    });

    return { initialNodes: nodes, initialEdges: edges };
  }, [graphData]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Synchronize React Flow state when new graph data is extracted
  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
    setSelectedEdge(null);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  // Handle Edge Click for inspection modal
  const onEdgeClick = useCallback((event, edge) => {
    setSelectedEdge(edge);
  }, []);

  // Export Handlers
  const handleExportJSON = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(graphData, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", "knowledge_graph.json");
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };

  const handleExportImage = (format) => {
    const element = document.querySelector('.react-flow__viewport');
    if (!element) return;

    const exportFunc = format === 'png' ? toPng : toSvg;
    exportFunc(element, { backgroundColor: '#0f172a' })
      .then((dataUrl) => {
        const link = document.createElement('a');
        link.download = `graph_export.${format}`;
        link.href = dataUrl;
        link.click();
      })
      .catch((err) => console.error(`Failed to export ${format}:`, err));
  };

  if (!graphData) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl h-[600px] flex items-center justify-center text-slate-500">
        Upload a document to render the knowledge graph.
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl h-[600px] relative overflow-hidden flex flex-col">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onEdgeClick={onEdgeClick}
        fitView
        colorMode="dark"
      >
        <Background color="#334155" gap={16} />
        <Controls className="bg-slate-800 border-slate-700 fill-slate-200" />
        
        {/* Export Control Panel */}
        <Panel position="top-right" className="flex gap-2">
          <button onClick={handleExportJSON} className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-200 border border-slate-700 rounded-lg transition-colors cursor-pointer">
            <Download className="w-3.5 h-3.5" /> JSON
          </button>
          <button onClick={() => handleExportImage('png')} className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-200 border border-slate-700 rounded-lg transition-colors cursor-pointer">
            <ImageIcon className="w-3.5 h-3.5" /> PNG
          </button>
          <button onClick={() => handleExportImage('svg')} className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-200 border border-slate-700 rounded-lg transition-colors cursor-pointer">
            <ImageIcon className="w-3.5 h-3.5" /> SVG
          </button>
        </Panel>
      </ReactFlow>

      {/* Edge Details Modal */}
      {selectedEdge && (
        <div className="absolute bottom-4 left-4 right-4 bg-slate-800/90 backdrop-blur-md border border-slate-700 p-4 rounded-xl shadow-2xl">
          <div className="flex justify-between items-start mb-2">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
              <Info className="w-4 h-4" /> Edge Reasoning
            </div>
            <button onClick={() => setSelectedEdge(null)} className="text-slate-400 hover:text-slate-200 text-xs font-bold">✕</button>
          </div>
          <p className="text-sm text-slate-200 mb-3">{selectedEdge.data.reasoning}</p>
          <div className="flex gap-4 text-xs font-mono">
            <span className="text-slate-400">Impact: <strong className={selectedEdge.data.impact === 'POSITIVE' ? 'text-emerald-400' : selectedEdge.data.impact === 'NEGATIVE' ? 'text-rose-400' : 'text-slate-200'}>{selectedEdge.data.impact}</strong></span>
            <span className="text-slate-400">Confidence: <strong className="text-cyan-400">{(selectedEdge.data.confidence * 100).toFixed(1)}%</strong></span>
          </div>
        </div>
      )}
    </div>
  );
}