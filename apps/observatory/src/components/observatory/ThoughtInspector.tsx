"use client";

import Link from "next/link";
import type { CognitiveScene, SceneNode } from "@/types/observatory";

function cleanPayload(payload: Record<string, unknown>) {
  const entries = Object.entries(payload).filter(([, value]) => value !== undefined && value !== null && value !== "");
  return Object.fromEntries(entries);
}

export function ThoughtInspector({
  node,
  scene,
  onClose,
}: {
  node: SceneNode | null;
  scene: CognitiveScene;
  onClose: () => void;
}) {
  if (!node) return null;
  const relations = scene.edges
    .filter((edge) => edge.source === node.id || edge.target === node.id)
    .map((edge) => {
      const outgoing = edge.source === node.id;
      const otherId = outgoing ? edge.target : edge.source;
      const other = scene.nodes.find((candidate) => candidate.id === otherId);
      return { edge, other, outgoing };
    });

  return (
    <aside className="thought-inspector" aria-live="polite" aria-label={`Inspect ${node.kind}`}>
      <div className="thought-inspector__header">
        <div>
          <div className="thought-inspector__chips">
            <span className={`kind-chip kind-${node.kind}`}>{node.kind}</span>
            <span className={`layer-chip layer-${node.layer}`}>{node.layer}</span>
          </div>
          <h2>{node.label}</h2>
          <p>{node.summary}</p>
        </div>
        <button type="button" className="inspector-close" onClick={onClose} aria-label="Close inspector">×</button>
      </div>

      {node.layer === "diagnostic" ? (
        <div className="thought-inspector__diagnostic-note">
          <span>DIAGNOSTIC CHANNEL</span>
          <p>This is real operational data, but it is intentionally isolated from cognitive activity so verification traffic does not masquerade as thought.</p>
        </div>
      ) : null}

      <div className="thought-inspector__identity">
        <span>IDENTITY</span>
        <code>{node.objectId}</code>
        {node.timestamp && <time dateTime={node.timestamp}>{new Date(node.timestamp).toLocaleString()}</time>}
      </div>

      <dl className="thought-inspector__metrics">
        {node.metrics.map((item) => (
          <div key={`${item.label}:${item.value}`} className={item.tone ? `tone-${item.tone}` : undefined}>
            <dt>{item.label}</dt>
            <dd>{item.value}</dd>
          </div>
        ))}
      </dl>

      <section className="thought-inspector__relations">
        <div className="inspector-section-title">
          <span>CAUSAL / GRAPH LINEAGE</span>
          <strong>{relations.length}</strong>
        </div>
        {relations.length === 0 ? (
          <p className="inspector-empty">Brain exposes no explicit relation for this object in the current read model. The Observatory therefore renders it independently rather than inventing lineage.</p>
        ) : (
          <ul>
            {relations.map(({ edge, other, outgoing }) => (
              <li key={edge.id}>
                <span>{outgoing ? "→" : "←"} {edge.relation}</span>
                <strong>{other?.label ?? "Unresolved object"}</strong>
              </li>
            ))}
          </ul>
        )}
      </section>

      <details className="thought-inspector__raw">
        <summary>Raw live payload</summary>
        <pre>{JSON.stringify(cleanPayload(node.payload), null, 2)}</pre>
      </details>

      {node.route && (
        <Link href={node.route} className="inspector-action">
          Open operator surface <span aria-hidden="true">↗</span>
        </Link>
      )}
    </aside>
  );
}
