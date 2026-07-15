import { useState, useMemo } from 'react'
import { ReactFlow, Background, Controls, type Node, type Edge } from '@xyflow/react'
import { useCaseNetwork, type NetworkNode, type NetworkEdge } from '@/hooks/useCaseNetwork'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import { Info, HelpCircle, Network, Link as LinkIcon, User, Layers } from 'lucide-react'

// Import React Flow styles inline to scope them cleanly
import '@xyflow/react/dist/style.css'

interface NetworkAnalysisPanelProps {
  caseId: string
}

export function NetworkAnalysisPanel({ caseId }: NetworkAnalysisPanelProps) {
  const { data: graphData, isLoading, error, refetch } = useCaseNetwork(caseId)

  // Selection states
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)

  // Map backend node structure to React Flow Node objects
  const flowNodes = useMemo<Node[]>(() => {
    if (!graphData) return []

    return graphData.nodes.map((node) => {
      // Determine style classes based on node type
      let bgStyle = 'bg-neutral-50 border-neutral-300 text-neutral-800'
      if (node.type === 'case') {
        bgStyle = 'bg-rose-50 border-rose-400 text-rose-800 font-semibold'
      } else if (node.type === 'person') {
        bgStyle = 'bg-sky-50 border-sky-400 text-sky-800'
      } else if (node.type === 'dependency') {
        bgStyle = 'bg-amber-50 border-amber-400 text-amber-800'
      }

      return {
        id: node.id,
        position: node.position,
        data: { label: node.data.label },
        className: `px-4 py-2 rounded-radius-md border shadow-sm text-small text-center ${bgStyle}`,
        // Disable dragging to prevent canvas layouts shifts for judges
        draggable: false,
      }
    })
  }, [graphData])

  // Map backend edge structure to React Flow Edge objects
  const flowEdges = useMemo<Edge[]>(() => {
    if (!graphData) return []

    return graphData.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      labelStyle: { fill: '#666666', fontSize: 10, fontWeight: 500 },
      style: { stroke: '#999999', strokeWidth: 1.5 },
      animated: edge.label === 'CASE_HAS_DEPENDENCY',
    }))
  }, [graphData])

  // Find currently selected node details
  const selectedNodeDetails = useMemo<NetworkNode | null>(() => {
    if (!graphData || !selectedNodeId) return null
    return graphData.nodes.find((n) => n.id === selectedNodeId) || null
  }, [graphData, selectedNodeId])

  // Find currently selected edge details
  const selectedEdgeDetails = useMemo<NetworkEdge | null>(() => {
    if (!graphData || !selectedEdgeId) return null
    return graphData.edges.find((e) => e.id === selectedEdgeId) || null
  }, [graphData, selectedEdgeId])

  // Find connections for selected node (deterministic join)
  const connectedNodes = useMemo(() => {
    if (!graphData || !selectedNodeId) return []

    const connections: { node: NetworkNode; relation: string }[] = []
    
    graphData.edges.forEach((edge) => {
      if (edge.source === selectedNodeId) {
        const targetNode = graphData.nodes.find((n) => n.id === edge.target)
        if (targetNode) {
          connections.push({ node: targetNode, relation: edge.label })
        }
      } else if (edge.target === selectedNodeId) {
        const sourceNode = graphData.nodes.find((n) => n.id === edge.source)
        if (sourceNode) {
          connections.push({ node: sourceNode, relation: edge.label })
        }
      }
    })

    return connections
  }, [graphData, selectedNodeId])

  // Edge label description resolver
  const getRelationExplanation = (label: string) => {
    switch (label) {
      case 'ACCUSED_IN':
        return 'Entity is identified as a primary accused party listed in the FIR.'
      case 'VICTIM_IN':
        return 'Entity is identified as the victim / complainant listed in the FIR.'
      case 'CASE_HAS_DEPENDENCY':
        return 'Case has an outstanding evidentiary requirement blocking chargesheet progression.'
      default:
        return 'Entity is linked to this case file.'
    }
  }

  if (isLoading) return <LoadingSkeleton layout="detail" />
  if (error) return <ErrorState message="Failed to load case investigation graph." onRetry={refetch} />
  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="py-12 border border-dashed border-neutral-300 rounded-radius-md bg-neutral-50 text-center">
        <Network className="mx-auto h-12 w-12 text-neutral-400 mb-4" />
        <h3 className="text-h2 font-semibold text-neutral-700">No graph data available</h3>
        <p className="text-body text-neutral-500 mt-1">
          No relational entities are registered for this case file in the prototype.
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 h-[500px]">
      {/* Network Canvas (Left) */}
      <div className="lg:col-span-2 rounded-radius-md border border-neutral-200 bg-neutral-50 h-full relative">
        <ReactFlow
          nodes={flowNodes}
          edges={flowEdges}
          onNodeClick={(_, node) => {
            setSelectedNodeId(node.id)
            setSelectedEdgeId(null)
          }}
          onEdgeClick={(_, edge) => {
            setSelectedEdgeId(edge.id)
            setSelectedNodeId(null)
          }}
          onPaneClick={() => {
            setSelectedNodeId(null)
            setSelectedEdgeId(null)
          }}
          fitView
        >
          <Background color="#ccc" gap={16} />
          <Controls showInteractive={false} />
        </ReactFlow>
        <div className="absolute top-4 left-4 bg-white/90 px-3 py-1.5 rounded-radius-sm border border-neutral-200 text-[10px] text-neutral-500 shadow-sm z-10 space-y-1">
          <div className="flex items-center"><span className="w-2 h-2 rounded-full bg-rose-400 mr-1.5" /> Case Object</div>
          <div className="flex items-center"><span className="w-2 h-2 rounded-full bg-sky-400 mr-1.5" /> Person Entity</div>
          <div className="flex items-center"><span className="w-2 h-2 rounded-full bg-amber-400 mr-1.5" /> Evidentiary Blocker</div>
        </div>
      </div>

      {/* Inspector Sidebar (Right) */}
      <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-5 overflow-y-auto flex flex-col h-full">
        {/* Node Inspect View */}
        {selectedNodeDetails && (
          <div className="space-y-5 flex-1">
            <div className="border-b border-neutral-200 pb-3">
              <span className="text-caption font-bold text-status-info uppercase tracking-wider">
                {selectedNodeDetails.type} entity
              </span>
              <h3 className="text-h2 font-bold text-neutral-900 mt-1">
                {selectedNodeDetails.data.label}
              </h3>
            </div>

            <div>
              <h4 className="text-caption font-semibold text-neutral-500 uppercase tracking-wider flex items-center gap-1.5">
                <Layers className="h-4 w-4" /> Attributes
              </h4>
              <dl className="mt-2 text-small space-y-1 text-neutral-700 bg-neutral-100 p-3 rounded-radius-sm">
                <div className="flex justify-between">
                  <dt className="text-neutral-500">ID Reference</dt>
                  <dd className="font-mono">{selectedNodeDetails.id}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-neutral-500">Node Class</dt>
                  <dd className="capitalize">{selectedNodeDetails.type}</dd>
                </div>
              </dl>
            </div>

            <div>
              <h4 className="text-caption font-semibold text-neutral-500 uppercase tracking-wider flex items-center gap-1.5">
                <LinkIcon className="h-4 w-4" /> Connected Relationships
              </h4>
              {connectedNodes.length === 0 ? (
                <p className="text-small text-neutral-500 mt-2">No active connections found.</p>
              ) : (
                <ul className="mt-2 space-y-2">
                  {connectedNodes.map(({ node, relation }) => (
                    <li 
                      key={node.id} 
                      className="text-small p-2 bg-white border border-neutral-200 rounded-radius-sm flex flex-col"
                    >
                      <span className="font-semibold text-neutral-800">{node.data.label}</span>
                      <span className="text-caption text-neutral-500 mt-0.5">
                        Relationship: <code className="bg-neutral-100 px-1 rounded text-[10px]">{relation}</code>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}

        {/* Edge Inspect View */}
        {selectedEdgeDetails && (
          <div className="space-y-5 flex-1">
            <div className="border-b border-neutral-200 pb-3">
              <span className="text-caption font-bold text-status-warning uppercase tracking-wider">
                Graph Link
              </span>
              <h3 className="text-h2 font-bold text-neutral-900 mt-1">
                {selectedEdgeDetails.label}
              </h3>
            </div>

            <div>
              <h4 className="text-caption font-semibold text-neutral-500 uppercase tracking-wider flex items-center gap-1.5">
                <Info className="h-4 w-4" /> Description
              </h4>
              <p className="text-small text-neutral-700 mt-2 leading-relaxed">
                {getRelationExplanation(selectedEdgeDetails.label)}
              </p>
            </div>

            <div>
              <h4 className="text-caption font-semibold text-neutral-500 uppercase tracking-wider flex items-center gap-1.5">
                <HelpCircle className="h-4 w-4" /> Supporting Evidence
              </h4>
              <div className="mt-2 p-3 border border-dashed border-neutral-300 rounded-radius-sm bg-neutral-100 text-center">
                <span className="text-caption font-semibold text-neutral-500">
                  Unavailable in current prototype
                </span>
                <p className="text-[10px] text-neutral-400 mt-0.5">Requires evidentiary log integration</p>
              </div>
            </div>
          </div>
        )}

        {/* No Selection Empty State */}
        {!selectedNodeDetails && !selectedEdgeDetails && (
          <div className="flex-1 flex flex-col justify-center items-center text-center py-12 text-neutral-500">
            <User className="h-10 w-10 text-neutral-400 mb-3" />
            <h4 className="font-semibold">Graph Inspector</h4>
            <p className="text-caption mt-1 max-w-xs leading-normal">
              Click any node or relationship link on the canvas to inspect entity characteristics and connection reasons.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
