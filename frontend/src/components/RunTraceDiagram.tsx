import { WORKSPACE_COPY } from '../copy';
import type { TraceStep, TraceTool } from '../types';
import './RunTraceDiagram.css';

// Fixed layout of the chat graph (backend/app/chat/graph.py). The trace from
// the API says which nodes and edges this reply actually used.
const NODES: Record<string, { x: number; y: number; label: string; terminal?: boolean }> = {
  __start__: { x: 150, y: 24, label: 'start', terminal: true },
  run_all_tools: { x: 150, y: 96, label: 'run_all_tools' },
  answer: { x: 150, y: 168, label: 'answer' },
  __end__: { x: 150, y: 240, label: 'end', terminal: true },
};

const EDGES: { from: string; to: string; conditional?: boolean }[] = [
  { from: '__start__', to: 'run_all_tools' },
  { from: 'run_all_tools', to: 'answer' },
  { from: 'answer', to: '__end__' },
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
  return `M ${a.x} ${a.y + H / 2} L ${b.x} ${b.y - H / 2}`;
}

const STEP_LABELS: Record<string, string> = {
  run_all_tools: 'Run every tool',
  answer: 'Write the reply',
  // Older API versions.
  agent: 'Model reasoning',
  tools: 'Run tools',
};

type ToolStatus = 'ok' | 'error' | 'not_applicable';

function toolStatus(tool: TraceTool): ToolStatus {
  if (tool.status === 'not_applicable' || tool.status === 'error' || tool.status === 'ok') return tool.status;
  return tool.ok === false ? 'error' : 'ok';
}

const STATUS_MARK: Record<ToolStatus, string> = { ok: '✓', error: '✕', not_applicable: '–' };
const STATUS_TEXT: Record<ToolStatus, string> = {
  ok: WORKSPACE_COPY.traceToolOk,
  error: WORKSPACE_COPY.traceToolError,
  not_applicable: WORKSPACE_COPY.traceToolNotApplicable,
};

function formatMs(ms?: number): string | null {
  if (ms === undefined) return null;
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`;
}

function formatArgs(args?: TraceTool['args']): string {
  if (!args) return '';
  return Object.entries(args).map(([key, value]) => `${key}=${String(value)}`).join(', ');
}

// Every step this reply took, as a vertical flow. Tool steps fan out into one
// chip per tool so parallel calls and failures are visible at a glance.
export function RunTimeline({ steps, skipped }: { steps: TraceStep[]; skipped: string[] }) {
  const total = steps.reduce((sum, step) => sum + (step.durationMs ?? 0), 0);
  const toolCalls = steps.filter((step) => step.node === 'tools' || step.node === 'run_all_tools')
    .reduce((n, step) => n + (step.tools ?? []).filter((tool) => toolStatus(tool) !== 'not_applicable').length, 0);
  return (
    <div className="run-timeline">
      <p className="run-timeline-head">
        {WORKSPACE_COPY.traceStepsTitle}
        <span className="run-timeline-meta">
          {steps.length} steps · {toolCalls} tool {toolCalls === 1 ? 'call' : 'calls'}{total ? ` · ${formatMs(total)}` : ''}
        </span>
      </p>
      <ol className="run-timeline-steps">
        <li className="rt-step rt-terminal"><span className="rt-dot" />start</li>
        {steps.map((step, index) => {
          const tools = step.tools ?? [];
          const runsTools = step.node === 'tools' || step.node === 'run_all_tools';
          const failed = runsTools && tools.some((tool) => toolStatus(tool) === 'error');
          const share = total && step.durationMs ? Math.max(4, Math.round((step.durationMs / total) * 100)) : 0;
          return (
            <li key={index} className={`rt-step rt-${step.node}${failed ? ' rt-failed' : ''}`}>
              <span className="rt-dot">{index + 1}</span>
              <div className="rt-card">
                <div className="rt-card-head">
                  <span className="rt-title">{STEP_LABELS[step.node] ?? step.node}</span>
                  <span className="mono rt-node">{step.node}</span>
                  {formatMs(step.durationMs) && <span className="rt-time">{formatMs(step.durationMs)}</span>}
                </div>
                {share > 0 && <div className="rt-bar"><span style={{ width: `${share}%` }} /></div>}
                {step.node === 'agent' && tools.length > 0 ? (
                  <ul className="rt-chips">
                    {tools.map((tool, i) => (
                      <li key={i} className="rt-chip rt-chip-request" title={formatArgs(tool.args)}>
                        <span className="mono">{tool.name}</span>
                        {formatArgs(tool.args) && <span className="rt-args mono">{formatArgs(tool.args)}</span>}
                      </li>
                    ))}
                  </ul>
                ) : runsTools && tools.length > 0 ? (
                  <ul className="rt-chips">
                    {tools.map((tool, i) => (
                      <li key={i} className={`rt-chip rt-chip-${toolStatus(tool)}`} title={formatArgs(tool.args)}>
                        <span aria-hidden="true">{STATUS_MARK[toolStatus(tool)]}</span>
                        <span className="mono">{tool.name}</span>
                        <span className="rt-args">{STATUS_TEXT[toolStatus(tool)]}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  step.detail && <p className="rt-detail">{step.detail}</p>
                )}
              </div>
            </li>
          );
        })}
        <li className="rt-step rt-terminal"><span className="rt-dot" />end</li>
      </ol>
      {skipped.length > 0 && (
        <p className="run-trace-skipped">{WORKSPACE_COPY.traceSkipped}: <span className="mono">{skipped.join(', ')}</span></p>
      )}
    </div>
  );
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
        <svg viewBox="0 0 300 264" className="run-trace-graph" role="img" aria-label={WORKSPACE_COPY.traceSummary}>
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
        {steps.length ? (
          <RunTimeline steps={steps} skipped={skipped} />
        ) : (
          <p className="field-hint">{WORKSPACE_COPY.traceEmpty}</p>
        )}
      </div>
    </details>
  );
}

export default RunTraceDiagram;
