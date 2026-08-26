import { EmptyState } from "@/components/EmptyState";

export default function GraphPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Graph Explorer</h1>
        <p className="text-xs text-cockpit-muted">
          Nodes and edges with weight, confidence, and formula-traced rewires.
        </p>
      </div>
      <EmptyState
        title="Graph projection not connected"
        description="Use POST /edges against the runtime. Neo4j projection is rebuildable from the event ledger."
        schemaHint="GraphNode · GraphEdge"
      />
    </div>
  );
}
