"use client";

import { useEffect, useMemo, useRef } from "react";
import type { CSSProperties } from "react";
import type { CognitiveScene, SceneEdge, SceneKind, SceneNode, SceneZone } from "@/types/observatory";

const COLORS: Record<SceneKind, string> = {
  organism: "#eef4fb",
  signal: "#4d9cff",
  belief: "#a98cff",
  prediction: "#5bddff",
  outcome: "#58dfa8",
  contradiction: "#ff7066",
  curiosity: "#f5bd63",
  source: "#91a6bd",
  approval: "#f3d782",
  opportunity: "#76e1ca",
  agency: "#b9caff",
  quarantine: "#ff7a68",
  goal: "#75c8ff",
  debate: "#ff8f82",
  idea: "#d79cff",
  dream: "#8ea7ff",
  development: "#68d6bb",
};

const DIAGNOSTIC = "#68798e";

function roundedRect(ctx: CanvasRenderingContext2D, x: number, y: number, width: number, height: number, radius: number) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + width, y, x + width, y + height, r);
  ctx.arcTo(x + width, y + height, x, y + height, r);
  ctx.arcTo(x, y + height, x, y, r);
  ctx.arcTo(x, y, x + width, y, r);
  ctx.closePath();
}

function drawPolygon(ctx: CanvasRenderingContext2D, x: number, y: number, radius: number, sides: number, rotation = -Math.PI / 2) {
  ctx.beginPath();
  for (let index = 0; index < sides; index += 1) {
    const angle = rotation + (index / sides) * Math.PI * 2;
    const px = x + Math.cos(angle) * radius;
    const py = y + Math.sin(angle) * radius;
    if (index === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }
  ctx.closePath();
}

function edgePath(ctx: CanvasRenderingContext2D, source: { x: number; y: number }, target: { x: number; y: number }, tension: boolean) {
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const bend = tension ? 0.18 : 0.07;
  const cx = (source.x + target.x) / 2 - dy * bend;
  const cy = (source.y + target.y) / 2 + dx * bend;
  ctx.beginPath();
  ctx.moveTo(source.x, source.y);
  ctx.quadraticCurveTo(cx, cy, target.x, target.y);
  return { x: cx, y: cy };
}

function nodePulse(node: SceneNode): number {
  if (node.layer === "diagnostic") return 0;
  if (node.kind !== "signal" && node.kind !== "contradiction") return 0;
  const metric = node.metrics.find((item) => item.label === (node.kind === "signal" ? "urgency" : "pressure"));
  return Math.max(0, Math.min(1, Number(metric?.value ?? 0)));
}

function zonePosition(zone: SceneZone["id"], mobile: boolean) {
  if (mobile) {
    return {
      perception: [0.045, 0.43],
      belief: [0.34, 0.29],
      curiosity: [0.34, 0.08],
      prediction: [0.72, 0.43],
      learning: [0.61, 0.7],
      agency: [0.39, 0.76],
      diagnostic: [0.04, 0.86],
    }[zone] as [number, number];
  }
  return {
    perception: [0.16, 0.16],
    belief: [0.37, 0.23],
    curiosity: [0.42, 0.065],
    prediction: [0.76, 0.16],
    learning: [0.72, 0.79],
    agency: [0.46, 0.86],
    diagnostic: [0.11, 0.795],
  }[zone] as [number, number];
}

function nodeColor(node: SceneNode): string {
  return node.layer === "diagnostic" ? DIAGNOSTIC : COLORS[node.kind];
}

export function CognitiveField({
  scene,
  selectedId,
  onSelect,
}: {
  scene: CognitiveScene;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const nodeMap = useMemo(() => new Map(scene.nodes.map((node) => [node.id, node])), [scene.nodes]);
  const animationKey = `${scene.activity}:${scene.nodes.length}:${scene.edges.length}:${scene.organism.stress}:${scene.organism.dominantGoalPressure}`;

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let frame = 0;
    let width = 1;
    let height = 1;
    let dpr = 1;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const isMobile = window.matchMedia("(max-width: 760px)").matches;
    const animate = !reduced && scene.activity > 0;

    const resize = () => {
      const bounds = container.getBoundingClientRect();
      width = Math.max(1, bounds.width);
      height = Math.max(1, bounds.height);
      dpr = Math.min(window.devicePixelRatio || 1, isMobile ? 1.5 : 2);
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const point = (node: SceneNode) => ({ x: node.x * width, y: node.y * height });
    const center = () => ({ x: width * 0.5, y: height * 0.49 });

    const drawReferenceField = () => {
      const c = center();
      const min = Math.min(width, height);
      ctx.save();

      const fieldGradient = ctx.createRadialGradient(c.x, c.y, 0, c.x, c.y, min * 0.43);
      fieldGradient.addColorStop(0, "rgba(55, 68, 92, .19)");
      fieldGradient.addColorStop(0.42, "rgba(25, 34, 50, .10)");
      fieldGradient.addColorStop(1, "rgba(4, 8, 14, 0)");
      ctx.fillStyle = fieldGradient;
      ctx.fillRect(0, 0, width, height);

      ctx.lineWidth = 1;
      [0.12, 0.195, 0.285].forEach((radiusFactor, index) => {
        const radius = min * radiusFactor;
        ctx.strokeStyle = `rgba(142, 165, 192, ${0.105 - index * 0.022})`;
        ctx.setLineDash(index === 2 ? [2, 8] : []);
        ctx.beginPath();
        ctx.ellipse(c.x, c.y, radius * 1.17, radius, 0, 0, Math.PI * 2);
        ctx.stroke();
      });
      ctx.setLineDash([]);

      // The central organism reads as a pressure instrument, not a decorative target.
      const pressureEntries = Object.entries(scene.organism.pressures);
      pressureEntries.forEach(([key, value], index) => {
        const angle = -Math.PI / 2 + (index / pressureEntries.length) * Math.PI * 2;
        const inner = min * 0.055;
        const outer = inner + min * (0.035 + value * 0.045);
        const x1 = c.x + Math.cos(angle) * inner;
        const y1 = c.y + Math.sin(angle) * inner;
        const x2 = c.x + Math.cos(angle) * outer;
        const y2 = c.y + Math.sin(angle) * outer;
        ctx.strokeStyle = value > 0.65 ? "rgba(255,112,102,.65)" : value > 0.35 ? "rgba(245,189,99,.50)" : "rgba(139,164,194,.24)";
        ctx.lineWidth = 1 + value * 2.2;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
        if (!isMobile && value > 0.05) {
          ctx.font = "8px ui-monospace, SFMono-Regular, Menlo, monospace";
          ctx.fillStyle = "rgba(150,170,193,.58)";
          ctx.textAlign = "center";
          ctx.fillText(key.toUpperCase(), c.x + Math.cos(angle) * (outer + 16), c.y + Math.sin(angle) * (outer + 16));
        }
      });

      const memoryAlpha = 0.04 + scene.memoryPressure * 0.14;
      ctx.strokeStyle = `rgba(169, 140, 255, ${memoryAlpha})`;
      ctx.lineWidth = 3 + scene.memoryPressure * 10;
      ctx.beginPath();
      ctx.ellipse(c.x, c.y, min * 0.155, min * 0.115, 0, 0, Math.PI * 2);
      ctx.stroke();

      const wm = Math.min(1, scene.workingMemorySize / 7);
      ctx.strokeStyle = `rgba(238,244,251,${0.1 + wm * 0.2})`;
      ctx.lineWidth = 1.5 + wm * 5;
      ctx.beginPath();
      ctx.arc(c.x, c.y, min * 0.073, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * Math.max(0.08, wm));
      ctx.stroke();

      const goalPressure = scene.organism.dominantGoalPressure;
      if (scene.organism.dominantGoal) {
        ctx.strokeStyle = `rgba(117,200,255,${0.2 + goalPressure * 0.5})`;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(c.x, c.y, min * 0.095, Math.PI * 1.05, Math.PI * (1.05 + 0.9 * Math.max(0.08, goalPressure)));
        ctx.stroke();
      }

      ctx.restore();
    };

    const drawZones = () => {
      ctx.save();
      ctx.textBaseline = "top";
      scene.zones.forEach((zone) => {
        const [x, y] = zonePosition(zone.id, isMobile);
        const active = zone.count > 0;
        const stateColor = zone.id === "diagnostic"
          ? "rgba(113,132,154,.68)"
          : active
            ? "rgba(176,197,220,.72)"
            : "rgba(116,137,161,.55)";
        ctx.fillStyle = stateColor;
        ctx.font = `${isMobile ? 8 : 9}px ui-monospace, SFMono-Regular, Menlo, monospace`;
        ctx.letterSpacing = "0px";
        ctx.fillText(`${zone.label}  ${zone.count} · ${zone.state.toUpperCase()}`, x * width, y * height);
        if (!isMobile && !active && zone.id !== "diagnostic") {
          ctx.font = "8px ui-monospace, SFMono-Regular, Menlo, monospace";
          ctx.fillStyle = "rgba(97,116,138,.42)";
          const short = zone.detail.length > 54 ? `${zone.detail.slice(0, 53)}…` : zone.detail;
          ctx.fillText(short, x * width, y * height + 15);
        }
      });
      ctx.restore();
    };

    const drawCoreText = () => {
      const c = center();
      const phase = scene.organism.phase ? scene.organism.phase.replaceAll("_", " ").toUpperCase() : "SELF STATE NOT SNAPSHOTTED";
      ctx.save();
      ctx.textAlign = "center";
      ctx.font = `${isMobile ? 8 : 9}px ui-monospace, SFMono-Regular, Menlo, monospace`;
      ctx.fillStyle = "rgba(206,218,231,.72)";
      ctx.fillText(phase, c.x, c.y + (isMobile ? 64 : 74));
      if (scene.organism.dominantGoal) {
        ctx.fillStyle = "rgba(117,200,255,.72)";
        ctx.fillText(`GOAL ${scene.organism.dominantGoal.replaceAll("_", " ").toUpperCase()} · ${scene.organism.dominantGoalPressure.toFixed(2)}`, c.x, c.y + (isMobile ? 77 : 89));
      }
      ctx.restore();
    };

    const drawArrow = (from: { x: number; y: number }, to: { x: number; y: number }, color: string, alpha: number) => {
      const angle = Math.atan2(to.y - from.y, to.x - from.x);
      const size = 5;
      ctx.save();
      ctx.fillStyle = color;
      ctx.globalAlpha = alpha;
      ctx.beginPath();
      ctx.moveTo(to.x, to.y);
      ctx.lineTo(to.x - Math.cos(angle - 0.55) * size, to.y - Math.sin(angle - 0.55) * size);
      ctx.lineTo(to.x - Math.cos(angle + 0.55) * size, to.y - Math.sin(angle + 0.55) * size);
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    };

    const drawEdge = (edge: SceneEdge, time: number) => {
      const sourceNode = nodeMap.get(edge.source);
      const targetNode = nodeMap.get(edge.target);
      if (!sourceNode || !targetNode) return;
      const source = point(sourceNode);
      const target = point(targetNode);
      const diagnostic = sourceNode.layer === "diagnostic" || targetNode.layer === "diagnostic";
      const color = edge.tension ? "#ff7066" : diagnostic ? DIAGNOSTIC : "#8fa9c8";
      const alpha = diagnostic ? 0.16 : 0.16 + edge.strength * 0.28;
      ctx.save();
      ctx.lineWidth = edge.tension ? 1.4 + edge.strength : 0.7 + edge.strength * 1.1;
      ctx.strokeStyle = edge.tension ? `rgba(255,112,102,${0.28 + edge.strength * 0.45})` : diagnostic ? "rgba(104,121,142,.20)" : `rgba(143,169,200,${alpha})`;
      if (edge.tension) {
        ctx.setLineDash([5, 6]);
        ctx.lineDashOffset = animate ? -(time / 90) % 22 : 0;
      }
      const control = edgePath(ctx, source, target, Boolean(edge.tension));
      ctx.stroke();
      drawArrow(control, target, color, Math.min(0.7, alpha + 0.2));
      if (!isMobile && !diagnostic) {
        ctx.setLineDash([]);
        ctx.font = "8px ui-monospace, SFMono-Regular, Menlo, monospace";
        ctx.fillStyle = edge.tension ? "rgba(255,142,132,.72)" : "rgba(132,154,179,.56)";
        ctx.fillText(edge.relation.toUpperCase(), control.x + 5, control.y + 4);
      }
      ctx.restore();
    };

    const drawSignal = (ctx2: CanvasRenderingContext2D, x: number, y: number, radius: number, color: string, diagnostic: boolean) => {
      if (diagnostic) {
        roundedRect(ctx2, x - radius * 0.7, y - radius * 0.7, radius * 1.4, radius * 1.4, 2);
        ctx2.stroke();
        ctx2.setLineDash([2, 3]);
        ctx2.beginPath();
        ctx2.arc(x, y, radius * 1.35, 0, Math.PI * 2);
        ctx2.stroke();
        ctx2.setLineDash([]);
        return;
      }
      ctx2.beginPath();
      ctx2.arc(x, y, radius * 0.48, 0, Math.PI * 2);
      ctx2.fill();
      ctx2.stroke();
      [0.82, 1.18].forEach((scale) => {
        ctx2.beginPath();
        ctx2.arc(x, y, radius * scale, -Math.PI * 0.62, Math.PI * 0.62);
        ctx2.stroke();
      });
      ctx2.strokeStyle = color;
    };

    const drawNode = (node: SceneNode, time: number) => {
      const { x, y } = point(node);
      const color = nodeColor(node);
      const pulse = nodePulse(node);
      const phase = pulse > 0 && animate ? (Math.sin(time / (620 - pulse * 300)) + 1) / 2 : 0;
      const radius = node.size + phase * pulse * 4;
      const selected = node.id === selectedId;
      const diagnostic = node.layer === "diagnostic";

      ctx.save();
      ctx.globalAlpha = diagnostic ? 0.72 : 1;
      if ((node.importance > 0.58 || selected) && !diagnostic) {
        ctx.globalCompositeOperation = "lighter";
        const haloRadius = radius * (2 + node.importance * 0.7);
        const gradient = ctx.createRadialGradient(x, y, radius * 0.2, x, y, haloRadius);
        gradient.addColorStop(0, `${color}${selected ? "52" : "26"}`);
        gradient.addColorStop(1, `${color}00`);
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(x, y, haloRadius, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalCompositeOperation = "source-over";
      }

      ctx.strokeStyle = color;
      ctx.fillStyle = `${color}${selected ? "36" : diagnostic ? "08" : "16"}`;
      ctx.lineWidth = selected ? 2.2 : diagnostic ? 0.9 : 1.2;
      ctx.shadowColor = selected ? color : "transparent";
      ctx.shadowBlur = selected ? 16 : 0;

      switch (node.kind) {
        case "signal":
          drawSignal(ctx, x, y, radius, color, diagnostic);
          break;
        case "belief":
          drawPolygon(ctx, x, y, radius, 6);
          ctx.fill(); ctx.stroke();
          ctx.beginPath(); ctx.arc(x, y, radius * 0.36, 0, Math.PI * 2); ctx.stroke();
          break;
        case "prediction":
          drawPolygon(ctx, x, y, radius, 4, 0);
          ctx.fill(); ctx.stroke();
          if (!diagnostic) {
            ctx.beginPath(); ctx.moveTo(x + radius, y); ctx.lineTo(x + radius * 2.2, y); ctx.stroke();
          }
          break;
        case "outcome":
          ctx.beginPath(); ctx.arc(x, y, radius, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
          ctx.beginPath(); ctx.arc(x, y, radius * 1.45, Math.PI * 0.2, Math.PI * 1.1); ctx.stroke();
          break;
        case "contradiction":
          ctx.beginPath(); ctx.arc(x - radius * 0.22, y, radius * 0.72, -1.1, 1.1); ctx.stroke();
          ctx.beginPath(); ctx.arc(x + radius * 0.22, y, radius * 0.72, Math.PI - 1.1, Math.PI + 1.1); ctx.stroke();
          ctx.beginPath(); ctx.moveTo(x - radius * 0.55, y - radius * 0.55); ctx.lineTo(x + radius * 0.55, y + radius * 0.55); ctx.stroke();
          break;
        case "curiosity":
          ctx.setLineDash([4, 4]);
          ctx.beginPath(); ctx.arc(x, y, radius, -Math.PI * 0.15, Math.PI * 1.45); ctx.stroke();
          ctx.setLineDash([]);
          ctx.beginPath(); ctx.arc(x + radius * 0.72, y - radius * 0.48, 2.2, 0, Math.PI * 2); ctx.fill();
          break;
        case "source":
          ctx.beginPath();
          ctx.moveTo(x + radius * 0.6, y - radius); ctx.lineTo(x - radius, y - radius); ctx.lineTo(x - radius, y + radius); ctx.lineTo(x + radius * 0.6, y + radius);
          ctx.stroke();
          break;
        case "approval":
          ctx.beginPath(); ctx.moveTo(x - radius * 0.65, y - radius); ctx.lineTo(x - radius * 0.65, y + radius); ctx.moveTo(x + radius * 0.65, y - radius); ctx.lineTo(x + radius * 0.65, y + radius); ctx.stroke();
          break;
        case "agency":
          ctx.beginPath(); ctx.moveTo(x - radius, y - radius * 0.7); ctx.lineTo(x, y); ctx.lineTo(x - radius, y + radius * 0.7); ctx.moveTo(x, y); ctx.lineTo(x + radius, y); ctx.stroke();
          break;
        case "goal":
          drawPolygon(ctx, x, y, radius, 3, -Math.PI / 2); ctx.stroke();
          ctx.beginPath(); ctx.arc(x, y, radius * 0.28, 0, Math.PI * 2); ctx.fill();
          break;
        case "debate":
          ctx.beginPath(); ctx.moveTo(x - radius, y - radius); ctx.lineTo(x - radius * 0.35, y); ctx.lineTo(x - radius, y + radius); ctx.moveTo(x + radius, y - radius); ctx.lineTo(x + radius * 0.35, y); ctx.lineTo(x + radius, y + radius); ctx.stroke();
          break;
        case "idea":
          for (let index = 0; index < 6; index += 1) {
            const angle = index / 6 * Math.PI * 2;
            ctx.beginPath(); ctx.moveTo(x + Math.cos(angle) * radius * 0.35, y + Math.sin(angle) * radius * 0.35); ctx.lineTo(x + Math.cos(angle) * radius, y + Math.sin(angle) * radius); ctx.stroke();
          }
          ctx.beginPath(); ctx.arc(x, y, radius * 0.32, 0, Math.PI * 2); ctx.fill();
          break;
        case "dream":
          ctx.beginPath(); ctx.arc(x, y, radius, -Math.PI / 2, Math.PI / 2); ctx.arc(x + radius * 0.38, y, radius * 0.82, Math.PI / 2, -Math.PI / 2, true); ctx.stroke();
          break;
        case "development":
          ctx.beginPath(); ctx.arc(x, y, radius, 0, Math.PI * 2); ctx.stroke();
          ctx.beginPath(); ctx.moveTo(x - radius * 0.45, y); ctx.lineTo(x - radius * 0.08, y + radius * 0.34); ctx.lineTo(x + radius * 0.52, y - radius * 0.42); ctx.stroke();
          break;
        case "quarantine":
          drawPolygon(ctx, x, y, radius, 8); ctx.stroke();
          ctx.beginPath(); ctx.moveTo(x - radius * 0.48, y - radius * 0.48); ctx.lineTo(x + radius * 0.48, y + radius * 0.48); ctx.moveTo(x + radius * 0.48, y - radius * 0.48); ctx.lineTo(x - radius * 0.48, y + radius * 0.48); ctx.stroke();
          break;
        case "opportunity":
          roundedRect(ctx, x - radius, y - radius * 0.7, radius * 2, radius * 1.4, radius * 0.25); ctx.fill(); ctx.stroke();
          break;
        case "organism":
          ctx.beginPath(); ctx.arc(x, y, radius, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
          ctx.globalAlpha *= 0.55;
          ctx.beginPath(); ctx.arc(x, y, radius * 0.54, 0, Math.PI * 2); ctx.stroke();
          break;
      }
      ctx.restore();
    };

    const drawLabels = () => {
      ctx.save();
      ctx.textBaseline = "top";
      scene.nodes.forEach((node) => {
        const selected = node.id === selectedId;
        if (node.layer === "diagnostic" && !selected) return;
        if (isMobile && !selected && node.kind !== "organism" && node.kind !== "goal") return;
        if (!selected && node.importance < 0.68) return;
        const { x, y } = point(node);
        const max = isMobile ? 20 : 38;
        const label = node.label.length > max ? `${node.label.slice(0, max - 1)}…` : node.label;
        ctx.font = `${isMobile ? 8 : 10}px ui-monospace, SFMono-Regular, Menlo, monospace`;
        ctx.fillStyle = selected ? "rgba(245,248,252,.96)" : "rgba(202,216,232,.72)";
        ctx.fillText(label, x + node.size + 8, y - 5);
      });
      ctx.restore();
    };

    const draw = (time = 0) => {
      ctx.clearRect(0, 0, width, height);
      drawReferenceField();
      drawZones();
      scene.edges.forEach((edge) => drawEdge(edge, time));
      scene.nodes.forEach((node) => drawNode(node, time));
      drawCoreText();
      drawLabels();
      if (animate) frame = requestAnimationFrame(draw);
    };

    resize();
    draw();
    const observer = new ResizeObserver(() => {
      resize();
      if (!animate) draw();
    });
    observer.observe(container);

    return () => {
      observer.disconnect();
      if (frame) cancelAnimationFrame(frame);
    };
  }, [animationKey, nodeMap, scene, selectedId]);

  const quiet = scene.cognitiveCount === 0;

  return (
    <div className="cognitive-field" ref={containerRef}>
      <canvas ref={canvasRef} className="cognitive-field__canvas" aria-hidden="true" />
      <div className="cognitive-field__targets" aria-label="Cognitive field objects">
        {scene.nodes.map((node) => {
          const hitSize = Math.max(44, node.size * 2 + 20);
          const style = {
            left: `${node.x * 100}%`,
            top: `${node.y * 100}%`,
            width: `${hitSize}px`,
            height: `${hitSize}px`,
            "--node-color": nodeColor(node),
          } as CSSProperties;
          return (
            <button
              type="button"
              key={node.id}
              className={`cognitive-field__target layer-${node.layer} ${node.id === selectedId ? "is-selected" : ""}`}
              style={style}
              onClick={() => onSelect(node.id)}
              aria-pressed={node.id === selectedId}
              aria-label={`${node.layer === "diagnostic" ? "diagnostic " : ""}${node.kind}: ${node.label}`}
              title={`${node.kind}: ${node.label}`}
            >
              <span className="sr-only">{node.summary}</span>
            </button>
          );
        })}
      </div>

      {quiet ? (
        <div className="cognitive-field__quiet-state" role="status">
          <span>COGNITIVE FIELD QUIET</span>
          <strong>No non-diagnostic cognitive objects are currently active in the exposed read models.</strong>
          {scene.diagnosticCount ? <em>{scene.diagnosticCount} operational record{scene.diagnosticCount === 1 ? " is" : "s are"} isolated in the diagnostic channel.</em> : null}
        </div>
      ) : null}
    </div>
  );
}
