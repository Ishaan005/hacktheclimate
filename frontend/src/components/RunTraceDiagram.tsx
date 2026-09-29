import { WORKSPACE_COPY } from '../copy';
import type { TraceStep } from '../types';
import './RunTraceDiagram.css';

// Fixed layout of the chat graph (backend/app/chat/graph.py). The trace from
// the API says which nodes and edges this reply actually used.
const NODES: Record<string, { x: number; y: number; label: string; terminal?: boolean }> = {
  __start__: { x: 150, y: 24, label: 'start', terminal: true },
  load_actions: { x: 150, y: 88, label: 'load_actions' },
  agent: { x: 150, y: 152, label: 'agent' },
  tools: { x: 62, y: 224, label: 'tools' },
  select_action: { x: 238, y: 224, label: 'select_action' },
  __end__: { x: 238, y: 288, label: 'end', terminal: true },
};

const EDGES: { from: string; to: string; conditional?: boolean }[] = [
  { from: '__start__', to: 'load_actions' },
  { from: 'load_actions', to: 'agent' },
  { from: 'agent', to: 'tools', conditional: true },
  { from: 'tools', to: 'agent' },
  { from: 'agent', to: 'select_action', conditional: true },
  { from: 'select_action', to: '__end__' },
];

const W = 112;
const H = 30;

// How many times each edge was taken, from consecutive trace steps.
export function edgeCounts(trace: TraceStep[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (let i = 1; i < trace.length; i += 1) {
    const key = `${trace[i - 1].node}->${trace[i].node}`;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return counts;
}

function edgePath(from: string, to: string): string {
  const a = NODES[from];
  const b = NODES[to];
  if (from === 'tools' && to === 'agent') {
    // Loop back up on the left so it does not overlap agent -> tools.
    return `M ${a.x - 20} ${a.y - H / 2} C ${a.x - 40} ${a.y - 40}, ${b.x - 70} ${b.y + 10}, ${b.x - W / 2} ${b.y}`;
  }
  return `M ${a.x} ${a.y + H / 2} L ${b.x} ${b.y - H / 2}`;
}

// The graph with this reply's path drawn on it, then the steps in order.
function RunTraceDiagram({ trace }: { trace: TraceStep[] }) {
  const visited = new Set(trace.map((step) => step.node));
  const counts = edgeCounts(trace);
  const steps = trace.filter((step) => step.node !== '__start__' && step.node !== '__end__');
  const skipped = Object.keys(NODES).filter((node) => !visited.has(node));
  return (
    <details className="run-trace" open>
      <summary>{WORKSPACE_COPY.traceTitle}</summary>
      <div className="run-trace-body">
        <svg viewBox="0 0 300 312" className="run-trace-graph" role="img" aria-label={WORKSPACE_COPY.traceSummary}>
          <defs>
            <marker id="trace-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor" />
            </marker>
          </defs>
          {EDGES.map((edge) => {
            const count = counts.get(`${edge.from}->${edge.to}`) ?? 0;
            const d = edgePath(edge.from, edge.to);
            const a = NODES[edge.from];
            const b = NODES[edge.to];
            return (
              <g key={`${edge.from}-${edge.to}`} className={count ? 'trace-edge trace-edge-used' : 'trace-edge'}>
                <path d={d} fill="none" strokeDasharray={edge.conditional ? '4 3' : undefined} markerEnd="url(#trace-arrow)" />
                {count > 1 && (
                  <text x={(a.x + b.x) / 2 + 8} y={(a.y + b.y) / 2} className="trace-count">×{count}</text>
                )}
              </g>
            );
          })}
          {Object.entries(NODES).map(([id, node]) => (
            <g key={id} className={visited.has(id) ? 'trace-node trace-node-used' : 'trace-node'}>
              <rect x={node.x - W / 2} y={node.y - H / 2} width={W} height={H} rx={node.terminal ? 15 : 5} />
              <text x={node.x} y={node.y + 4} textAnchor="middle">{node.label}</text>
            </g>
          ))}
        </svg>
        <ol className="run-trace-steps">
          {steps.map((step, index) => (
            <li key={index}>
              <span className="mono">{step.node}</span>
              {step.detail && <span className="run-trace-detail"> — {step.detail}</span>}
            </li>
          ))}
          {skipped.length > 0 && (
            <li className="run-trace-skipped">{WORKSPACE_COPY.traceSkipped}: <span className="mono">{skipped.join(', ')}</span></li>
          )}
        </ol>
      </div>
    </details>
  );
}

export default RunTraceDiagram;
