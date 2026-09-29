import { SEARCH_COPY } from '../../decision/copy/search';
import { FAMILY_LABEL, SUGGESTIONS } from '../../decision/scope';
import type { Suggestion } from '../../decision/scope';
import type { ScenarioFamily } from '../../decision/types';

type Props = {
  // Suggestion keys already under review; they are not offered again.
  exclude: string[];
  onPick: (suggestion: Suggestion) => void;
};

const FAMILIES = Object.keys(FAMILY_LABEL) as ScenarioFamily[];

// Suggested situations from the locked scope, grouped by family. The screen
// shows the plain-language text only.
function SuggestionList({ exclude, onPick }: Props) {
  return (
    <div className="search-suggestions" role="region" aria-labelledby="search-suggestions-title">
      <h3 id="search-suggestions-title" className="search-suggestions-title">{SEARCH_COPY.suggestionsHeading}</h3>
      {FAMILIES.map((family) => {
        const items = SUGGESTIONS.filter((item) => item.family === family && !exclude.includes(item.key));
        if (!items.length) return null;
        const titleId = `search-family-${family}`;
        return (
          <div key={family} className="search-family" role="group" aria-labelledby={titleId}>
            <h4 id={titleId} className="eyebrow">{FAMILY_LABEL[family]}</h4>
            <ul className="search-suggestion-list">
              {items.map((item) => (
                <li key={item.key}>
                  <button type="button" className="search-suggestion" onClick={() => onPick(item)}>
                    {item.text}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}

export default SuggestionList;
