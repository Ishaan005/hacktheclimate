import { SOURCE_KIND_LABEL } from '../../decision/copy/shared';
import { TOP_BAR_COPY } from '../../decision/copy/topBar';
import type { DataSourceKind } from '../../decision/types';
import './TopBar.css';

type Props = {
  kind: DataSourceKind;
  validated: boolean;
};

// Only a fully assessed live result gets the live (green) style. A plain live
// feed, a demonstration, a planning case and no connection each look
// different, so a demonstration never reads as live.
function SourceBadge({ kind, validated }: Props) {
  const liveValidated = kind === 'live' && validated;
  const tone = kind === 'live' ? (liveValidated ? 'live' : 'live-unvalidated') : kind.replaceAll('_', '-');
  const label = kind === 'live' && !validated ? TOP_BAR_COPY.liveFeed : SOURCE_KIND_LABEL[kind];
  return (
    <span className={`chip source-badge source-badge-${tone}`} data-source-kind={kind} data-validated={liveValidated}>
      {label}
    </span>
  );
}

export default SourceBadge;
