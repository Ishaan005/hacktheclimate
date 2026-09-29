import { WORKSPACE_COPY } from '../copy';
import { formatDayTime, formatTimeRange } from '../format';
import type { WorkspaceScenario } from '../types';

function ScenarioHeader({ scenario }: { scenario: WorkspaceScenario }) {
  const illustrative = scenario.source === 'illustrative';
  const demo = scenario.source === 'demo';
  return (
    <header className="scenario-header">
      <div className="scenario-header-main">
        <p className="scenario-header-chips">
          <span className="chip chip-advisory" title={WORKSPACE_COPY.advisoryNote}>{WORKSPACE_COPY.advisory}</span>
          <span className={`chip ${illustrative || demo ? 'chip-unknown' : 'chip-neutral'}`}>
            {illustrative ? WORKSPACE_COPY.illustrative : demo ? WORKSPACE_COPY.demo : WORKSPACE_COPY.live}
          </span>
        </p>
        <h2 id="workspace-heading">{scenario.title}</h2>
        <p className="scenario-header-meta">
          <span className="mono">{formatTimeRange(scenario.intervalStart, scenario.intervalEnd)}</span>
          <span>{WORKSPACE_COPY.lastModelRun}: <span className="mono">{formatDayTime(scenario.modelRunAt)}</span></span>
          <span>{WORKSPACE_COPY.timeZoneNote}</span>
        </p>
        <p className="scenario-header-summary">{scenario.summary}</p>
        {illustrative && <p className="scenario-header-note">{WORKSPACE_COPY.illustrativeNote}</p>}
        {demo && <p className="scenario-header-note">{WORKSPACE_COPY.demoNote}</p>}
      </div>
      <label className="comparison-select">
        <span>{WORKSPACE_COPY.comparisonLabel}</span>
        <select defaultValue="baseline">
          <option value="baseline">{WORKSPACE_COPY.comparisonBaseline}</option>
        </select>
      </label>
    </header>
  );
}

export default ScenarioHeader;
