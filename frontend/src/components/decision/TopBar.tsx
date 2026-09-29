import { DATA_STATUS_LABEL } from '../../decision/copy/shared';
import { TOP_BAR_COPY } from '../../decision/copy/topBar';
import { DEMO_SITES, siteById } from '../../decision/sites';
import type { DataStatus, ViewMode, WorkspaceContext } from '../../decision/types';
import { formatDateTime, formatWindow } from '../../format';
import SourceBadge from './SourceBadge';
import './TopBar.css';

type Props = {
  context: WorkspaceContext | null;
  view: ViewMode;
  siteId: string | null;
  validated: boolean;
  onViewChange: (view: ViewMode, siteId: string | null) => void;
};

const VIEWS: ViewMode[] = ['national', 'site'];

// Only current data looks settled. Stale, missing and conflicting are amber.
const STATUS_TONE: Record<DataStatus, string> = {
  current: 'chip',
  stale: 'chip chip-unknown',
  missing: 'chip chip-unknown',
  conflicting: 'chip chip-unknown',
};

// Section 1 of the brief: choose the view, then see where, when and from
// which source the assessment comes. Both views show the same status fields.
function TopBar({ context, view, siteId, validated, onViewChange }: Props) {
  const site = view === 'site' ? siteById(siteId) : undefined;
  // Use the assessment's site details only when they are for this site.
  const contextForSite = context && context.view === 'site' && context.siteId === siteId ? context : null;
  const location = view === 'site' ? site?.name ?? TOP_BAR_COPY.noSite : TOP_BAR_COPY.allIsland;

  function selectView(next: ViewMode) {
    if (next === view) return;
    onViewChange(next, next === 'site' ? siteId ?? DEMO_SITES[0].id : null);
  }

  return (
    <header className="top-bar">
      {/* One band: toggle, optional site picker, then the status fields. */}
      <div className="top-bar-row">
        <fieldset className="top-bar-views">
          <legend className="visually-hidden">{TOP_BAR_COPY.viewLegend}</legend>
          {VIEWS.map((option) => (
            <label
              key={option}
              className={`top-bar-view${option === view ? ' top-bar-view-selected' : ''}`}
              title={TOP_BAR_COPY.viewHint[option]}
            >
              <input
                type="radio"
                name="workspace-view"
                value={option}
                checked={option === view}
                aria-labelledby={`top-bar-view-${option}`}
                aria-describedby={`top-bar-view-${option}-hint`}
                onChange={() => selectView(option)}
              />
              <span id={`top-bar-view-${option}`}>{TOP_BAR_COPY.viewLabel[option]}</span>
              <span id={`top-bar-view-${option}-hint`} className="visually-hidden">{TOP_BAR_COPY.viewHint[option]}</span>
            </label>
          ))}
        </fieldset>

        {view === 'site' && (
          <div className="field top-bar-site">
            <label htmlFor="top-bar-site" className="top-bar-site-label">{TOP_BAR_COPY.siteLabel}</label>
            <select
              id="top-bar-site"
              className="input"
              value={site?.id ?? ''}
              onChange={(event) => onViewChange('site', event.target.value)}
            >
              {!site && <option value="" disabled>{TOP_BAR_COPY.noSite}</option>}
              {DEMO_SITES.map((option) => (
                <option key={option.id} value={option.id}>{option.name}</option>
              ))}
            </select>
          </div>
        )}

        <dl className="fields top-bar-fields">
          <div>
            <dt>{TOP_BAR_COPY.location}</dt>
            <dd>{location}</dd>
          </div>
          {view === 'site' && site && (
            <>
              <div>
                <dt>{TOP_BAR_COPY.connection}</dt>
                <dd>{contextForSite?.siteConnection ?? site.connection}</dd>
              </div>
              <div>
                <dt>{TOP_BAR_COPY.limitingRoute}</dt>
                <dd>{contextForSite?.limitingRoute ?? site.limitingRoute}</dd>
              </div>
            </>
          )}
          <div>
            <dt>{TOP_BAR_COPY.currentTime}</dt>
            <dd className="top-bar-time">{context ? formatDateTime(context.currentTime) : <Placeholder />}</dd>
          </div>
          <div className="top-bar-field-window">
            <dt>{TOP_BAR_COPY.window}</dt>
            <dd className="top-bar-time">{context ? formatWindow(context.windowStart, context.windowEnd) : <Placeholder />}</dd>
          </div>
          <div>
            <dt>{TOP_BAR_COPY.dataStatus}</dt>
            <dd>
              {context
                ? <span className={STATUS_TONE[context.dataStatus]}>{DATA_STATUS_LABEL[context.dataStatus]}</span>
                : <Placeholder />}
            </dd>
          </div>
          <div>
            <dt>{TOP_BAR_COPY.source}</dt>
            <dd>{context ? <SourceBadge kind={context.sourceKind} validated={validated} /> : <Placeholder />}</dd>
          </div>
        </dl>
      </div>

      {view === 'site' && <p className="field-hint top-bar-note">{TOP_BAR_COPY.siteAllIslandNote}</p>}
    </header>
  );
}

function Placeholder() {
  return <span className="top-bar-placeholder">{TOP_BAR_COPY.noAssessment}</span>;
}

export default TopBar;
