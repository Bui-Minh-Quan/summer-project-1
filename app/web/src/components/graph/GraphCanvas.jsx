import React, { useCallback, useMemo, useState, useEffect } from 'react';
import { 
  ReactFlow, 
  Controls, 
  Background, 
  MarkerType, 
  useNodesState, 
  useEdgesState, 
  Panel,
  Handle,
  Position
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { toPng, toSvg } from 'html-to-image';
import { Download, Image as ImageIcon, Info } from 'lucide-react';

// FIX: Added Handle anchors for edges
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
    <div className={`px-4 py-2.5 shadow-lg rounded-xl border-2 backdrop-blur-md min-w-[140px] text-center relative ${colorClass}`}>
      <Handle type="target" position={Position.Top} id="top" className="!bg-slate-400 !w-2.5 !h-2.5 !border-2 !border-slate-900" />
      <div className="text-[9px] uppercase tracking-widest opacity-80 mb-0.5">{data.type}</div>
      <div className="font-bold text-sm">{data.label}</div>
      <Handle type="source" position={Position.Bottom} id="bottom" className="!bg-slate-400 !w-2.5 !h-2.5 !border-2 !border-slate-900" />
    </div>
  );
};

const nodeTypes = { custom: CustomNode };

export default function GraphCanvas({ graphData }) {
  const [selectedEdge, setSelectedEdge] = useState(null);

  const { initialNodes, initialEdges } = useMemo(() => {
    if (!graphData || !graphData.nodes) return { initialNodes: [], initialEdges: [] };

    // FIX: Map raw string IDs (with spaces/accents) to clean ASCII keys
    const idMap = new Map();
    graphData.nodes.forEach((n, idx) => idMap.set(n.id, `node-${idx}`));

    const radius = Math.max(250, graphData.nodes.length * 35);
    const centerX = 400;
    const centerY = 300;

    const nodes = graphData.nodes.map((n, index) => {
      const angle = (index / graphData.nodes.length) * 2 * Math.PI;
      return {
        id: idMap.get(n.id) || `node-${index}`,
        type: 'custom',
        position: { x: centerX + radius * Math.cos(angle), y: centerY + radius * Math.sin(angle) },
        data: { label: n.label, type: n.type },
      };
    });

    const edges = graphData.edges.map((e, index) => {
      const color = e.impact === 'POSITIVE' ? '#10b981' : e.impact === 'NEGATIVE' ? '#f43f5e' : '#64748b';
      return {
        id: `e-${index}`,
        source: idMap.get(e.source),
        target: idMap.get(e.target),
        label: e.label,
        animated: true,
        style: { stroke: color, strokeWidth: 2.5 },
        labelStyle: { fill: '#ffffff', fontWeight: 700, fontSize: 12 },
        labelBgStyle: { fill: '#0f172a', stroke: '#334155', strokeWidth: 1, rx: 6, ry: 6 },
        labelBgPadding: [8, 4],
        markerEnd: { type: MarkerType.ArrowClosed, color: color, width: 18, height: 18 },
        data: { reasoning: e.reasoning, confidence: e.confidence, impact: e.impact },
      };
    });

    return { initialNodes: nodes, initialEdges: edges };
  }, [graphData]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
    setSelectedEdge(null);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const onEdgeClick = useCallback((event, edge) => { setSelectedEdge(edge); }, []);

  const handleExportJSON = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(graphData, null, 2));
    const a = document.createElement('a');
    a.href = dataStr;
    a.download = "knowledge_graph.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
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
      }).catch(err => console.error(err));
  };

  if (!graphData) return <div className="bg-slate-900 border border-slate-800 rounded-2xl h-[600px] flex items-center justify-center text-slate-500">Upload a document to render the knowledge graph.</div>;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl h-[600px] relative overflow-hidden flex flex-col">
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onEdgeClick={onEdgeClick} fitView colorMode="dark">
        <Background color="#334155" gap={16} />
        <Controls className="bg-slate-800 border-slate-700 fill-slate-200" />
        <Panel position="top-right" className="flex gap-2">
          <button onClick={handleExportJSON} className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-200 border border-slate-700 rounded-lg"><Download className="w-3.5 h-3.5" /> JSON</button>
          <button onClick={() => handleExportImage('png')} className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-200 border border-slate-700 rounded-lg"><ImageIcon className="w-3.5 h-3.5" /> PNG</button>
          <button onClick={() => handleExportImage('svg')} className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-200 border border-slate-700 rounded-lg"><ImageIcon className="w-3.5 h-3.5" /> SVG</button>
        </Panel>
      </ReactFlow>

      {selectedEdge && (
        <div className="absolute bottom-4 left-4 right-4 bg-slate-800/90 backdrop-blur-md border border-slate-700 p-4 rounded-xl shadow-2xl">
          <div className="flex justify-between items-start mb-2">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm"><Info className="w-4 h-4" /> Edge Reasoning</div>
            <button onClick={() => setSelectedEdge(null)} className="text-slate-400 hover:text-slate-200 text-xs font-bold cursor-pointer">✕</button>
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