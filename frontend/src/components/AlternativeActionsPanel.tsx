import { ACTION_FAMILY_LABEL, EXECUTABILITY_LABEL, WORKSPACE_COPY } from '../copy';
import { formatEur, formatNumber } from '../format';
import { instructionText } from '../scenarios';
import type { AlternativeAction } from '../types';
import StatusChip from './StatusChip';

type Props = {
  alternatives: AlternativeAction[];
  // With a recommendation the alternatives rank from 2; without one they are
  // all rejected and rank from 1.
  hasRecommendation: boolean;
};

// Secondary to the recommended action: plain surface, smaller type and one
// row per option, so the recommendation stays the obvious choice.
function AlternativeActionsPanel({ alternatives, hasRecommendation }: Props) {
  if (alternatives.length === 0) return null;
  const firstRank = hasRecommendation ? 2 : 1;
  const title = hasRecommendation ? WORKSPACE_COPY.alternativesTitle : WORKSPACE_COPY.alternativesRejectedTitle;
  return (
    <section id="alternative-actions" className="card card-alternatives" aria-labelledby="alternatives-heading">
      <h3 id="alternatives-heading" className="card-kicker">
        {title}
        <span className="alternatives-count">{alternatives.length}</span>
      </h3>
      <div className="table-scroll">
        <table className="alternatives-table">
          <thead>
            <tr>
              <th scope="col">Rank</th>
              <th scope="col">Action</th>
              <th scope="col">Security result</th>
              <th scope="col" className="num">Dispatch-down waste</th>
              <th scope="col" className="num">Net financial value</th>
              <th scope="col">{WORKSPACE_COPY.alternativesWhyLower}</th>
            </tr>
          </thead>
          <tbody>
            {alternatives.map((alternative, i) => {
              const { action } = alternative;
              const rank = firstRank + i;
              return (
                <tr key={`${action.family}-${action.assetName}`}>
                  <td className="mono alternatives-rank">#{rank}</td>
                  <th scope="row">
                    <span className="alternatives-chips">
                      <span className="chip chip-neutral">{ACTION_FAMILY_LABEL[action.family]}</span>
                      {action.executability === 'conditional' && (
                        <span className="chip chip-unknown">{EXECUTABILITY_LABEL[action.executability]}</span>
                      )}
                    </span>
                    <span className="alternatives-instruction">{instructionText(action)}</span>
                  </th>
                  <td>
                    <StatusChip status={alternative.postAction.securityResult} prefix={`Rank ${rank} security result`} />
                  </td>
                  <td className="num">{formatNumber(alternative.postAction.dispatchDownWasteMwh, 'MWh')}</td>
                  <td className="num">{formatEur(alternative.netFinancialValueEur)}</td>
                  <td>
                    <ul className="alternatives-reasons">
                      {alternative.lowerRankReasons.map((reason) => <li key={reason}>{reason}</li>)}
                    </ul>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default AlternativeActionsPanel;
