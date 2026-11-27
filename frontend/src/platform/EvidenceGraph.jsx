import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  Position,
} from "reactflow";
import "reactflow/dist/style.css";
import { dateTime, shortId } from "./client.mjs";

export default function EvidenceGraph({ decision, cutoff }) {
  const data = useMemo(() => {
    const rows = decision.result.evidence.edges.filter(
      (edge) => edge.ts <= cutoff,
    );
    const ids = [
      ...new Set([
        decision.account_id,
        ...rows.flatMap((edge) => [edge.source, edge.target]),
      ]),
    ].sort();
    const nodes = ids.map((id, i) => ({
      id,
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      position: { x: (i % 4) * 220, y: Math.floor(i / 4) * 95 },
      data: {
        label: (
          <span title={id}>
            {shortId(id)}
            {id === decision.account_id ? (
              <small>Selected account</small>
            ) : null}
          </span>
        ),
      },
      className: id === decision.account_id ? "selected-account" : "",
    }));
    const edges = rows.map((row, i) => ({
      id: `${row.transaction_id}-${i}`,
      source: row.source,
      target: row.target,
      label: `${row.currency || "currency not recorded"} ${Number(row.amount).toLocaleString()}`,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: "#666", strokeWidth: 1.5 },
      labelStyle: { fontSize: 11, fill: "#222" },
    }));
    return { nodes, edges };
  }, [decision, cutoff]);
  return (
    <>
      <div
        className="evidence-canvas"
        role="region"
        aria-label="Observed account-flow evidence"
      >
        <ReactFlow
          key={decision.decision_id}
          nodes={data.nodes}
          edges={data.edges}
          fitView
          minZoom={0.2}
          maxZoom={2}
          nodesDraggable={false}
          nodesConnectable={false}
          deleteKeyCode={null}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#ddd" gap={22} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <p className="meta">
        Observed context through {dateTime(cutoff)}. Not a causal attribution or
        confirmed typology.
      </p>
      {decision.result.evidence.truncated_for_display ? (
        <p className="inline-warning">
          Display is truncated; this is not the complete evidence graph.
        </p>
      ) : null}
    </>
  );
}
