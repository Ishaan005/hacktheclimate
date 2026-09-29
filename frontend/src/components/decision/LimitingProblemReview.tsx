import { SEARCH_COPY } from '../../decision/copy/search';
import { FAMILY_LABEL, suggestionByKey } from '../../decision/scope';
import type { BindingCondition } from '../../decision/types';

type Props = {
  // Stable row ID; also scopes the title ID.
  rowId: string;
  condition: BindingCondition;
  onRemove: () => void;
};

// One limiting condition the app matched. The operator only confirms or
// removes it. Its details (route, outage, timing, SNSP drivers,
// jurisdiction) come from connected feeds such as SCADA and show in the
// situation table after assessment. Only the plain-language text shows; the
// scenario ID stays internal.
function LimitingProblemReview({ rowId, condition, onRemove }: Props) {
  const suggestion = suggestionByKey(condition.situationKey);
  const text = suggestion?.text ?? '';
  const family = suggestion?.family;
  const titleId = `${rowId}-title`;

  return (
    <li className="review-row" role="group" aria-labelledby={titleId}>
      <div className="review-row-header">
        <div>
          {family && <p className="eyebrow">{FAMILY_LABEL[family]}</p>}
          <p id={titleId} className="review-row-title">{text}</p>
        </div>
        <button type="button" className="button-secondary" aria-label={SEARCH_COPY.removeLabel(text)} onClick={onRemove}>
          {SEARCH_COPY.remove}
        </button>
      </div>
    </li>
  );
}

export default LimitingProblemReview;
