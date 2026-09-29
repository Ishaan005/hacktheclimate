import { DATA_STATUS_LABEL } from '../../decision/copy/shared';
import { TOP_BAR_COPY } from '../../decision/copy/topBar';
import { DEMO_SITES, siteById } from '../../decision/sites';
import { isDemoSource } from '../../decision/source';
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

const VIEWS: ViewMode[] = ['national', 'precise', 'site'];

// Only current data looks settled. Stale, missing and conflicting are amber.
const STATUS_TONE: Record<DataStatus, string> = {
  current: 'chip',
  stale: 'chip chip-unknown',
  missing: 'chip chip-unknown',
  conflicting: 'chip chip-unknown',
  modeled: 'chip chip-unknown',
};

// Section 1 of the brief: choose the view, then see where, when and from
// which source the assessment comes. Both views show the same status fields.
function TopBar({ context, view, siteId, validated, onViewChange }: Props) {
  const demo = context !== null && isDemoSource(context.sourceKind);
  const site = view !== 'national' ? siteById(siteId) : undefined;
  // Use the assessment's site details only when they are for this site.
  const contextForSite = context && context.view === view && context.siteId === siteId ? context : null;
  const location = view !== 'national' ? site?.name ?? TOP_BAR_COPY.noSite : TOP_BAR_COPY.allIsland;

  function selectView(next: ViewMode) {
    if (next === view) return;
    onViewChange(next, next === 'national' ? null : siteId ?? DEMO_SITES[0].id);
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
          {view !== 'national' && site && (
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
          {context && <div>
            <dt>{demo ? 'Assessment time' : TOP_BAR_COPY.currentTime}</dt>
            <dd className="top-bar-time">{formatDateTime(context.currentTime)}</dd>
          </div>}
          {context && <div className="top-bar-field-window">
            <dt>{TOP_BAR_COPY.window}</dt>
            <dd className="top-bar-time">{formatWindow(context.windowStart, context.windowEnd)}</dd>
          </div>}
          {!demo && context && <div>
            <dt>{TOP_BAR_COPY.dataStatus}</dt>
            <dd><span className={STATUS_TONE[context.dataStatus]}>{DATA_STATUS_LABEL[context.dataStatus]}</span></dd>
          </div>}
          {!demo && context && <div>
            <dt>{TOP_BAR_COPY.source}</dt>
            <dd><SourceBadge kind={context.sourceKind} validated={validated} /></dd>
          </div>}
        </dl>
      </div>

      {view === 'precise' && (
        <div className="top-bar-plants" role="group" aria-label="Plants in planning case">
          {DEMO_SITES.map((plant) => (
            <button
              key={plant.id}
              type="button"
              className={`top-bar-plant${plant.id === siteId ? ' top-bar-plant-selected' : ''}`}
              aria-pressed={plant.id === siteId}
              onClick={() => onViewChange('precise', plant.id)}
            >
              {plant.name}
            </button>
          ))}
        </div>
      )}
      {view !== 'national' && <p className="field-hint top-bar-note">{TOP_BAR_COPY.siteAllIslandNote}</p>}
    </header>
  );
}

export default TopBar;
