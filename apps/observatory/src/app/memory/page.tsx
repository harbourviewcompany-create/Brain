import { EmptyState } from "@/components/EmptyState";

export default function MemoryPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Memory Console</h1>
        <p className="text-xs text-cockpit-muted">
          Working · episodic · semantic · procedural · emotional · social
        </p>
      </div>
      <EmptyState
        title="Memory projections not live"
        description="Bounded working memory and other memory kinds will appear when persistence adapters expose them."
        schemaHint="MemoryObject · MemoryKind"
      />
    </div>
  );
}
