import { WORKSPACE_COPY } from '../copy';
import type { AssistantReply } from '../types';

const RECOMMENDED = /^\s*\**\s*Recommended action:\s*\**\s*(.+)$/i;

// Splits the assistant's reply into its answer and the select_action
// recommendation line, so the recommendation stands out.
export function splitReply(text: string): { body: string[]; recommendation: string | null } {
  const body: string[] = [];
  let recommendation: string | null = null;
  for (const line of text.split('\n')) {
    const match = line.match(RECOMMENDED);
    if (match && recommendation === null) recommendation = match[1].replace(/\*+$/, '').trim();
    else if (line.trim()) body.push(line);
  }
  return { body, recommendation };
}

// The LangGraph assistant's reply: what it found, the action it picked and
// which tools supplied the numbers.
function AssistantReplyCard({ reply }: { reply: AssistantReply }) {
  const { body, recommendation } = splitReply(reply.text);
  return (
    <section className="card assistant-reply" aria-labelledby="assistant-heading">
      <h2 id="assistant-heading" className="card-kicker">
        {WORKSPACE_COPY.assistantTitle}
        <span className="chip chip-neutral">{reply.model}</span>
      </h2>
      {body.map((line, index) => <p key={index} className="assistant-line">{line}</p>)}
      {recommendation && (
        <div className="assistant-recommendation">
          <p className="field-label">{WORKSPACE_COPY.assistantRecommended}</p>
          <p className="instruction">{recommendation}</p>
        </div>
      )}
      <dl className="fields">
        <div>
          <dt>{WORKSPACE_COPY.assistantToolsUsed}</dt>
          <dd className="mono">{reply.toolsUsed.length ? reply.toolsUsed.join(', ') : WORKSPACE_COPY.assistantNoTools}</dd>
        </div>
      </dl>
      <p className="field-hint">{WORKSPACE_COPY.assistantNote}</p>
    </section>
  );
}

export default AssistantReplyCard;
