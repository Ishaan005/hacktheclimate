import { WORKSPACE_COPY } from '../copy';

export type DetailField = {
  label: string;
  value: string;
  // Mono for timestamps and technical values that line up across rows.
  mono?: boolean;
};

type Props = {
  fields: DetailField[];
  costs?: DetailField[];
};

function FieldList({ fields, label }: { fields: DetailField[]; label?: string }) {
  return (
    <dl className="fields" aria-label={label}>
      {fields.map((field) => (
        <div key={field.label}>
          <dt>{field.label}</dt>
          <dd className={field.mono ? 'mono' : undefined}>{field.value}</dd>
        </div>
      ))}
    </dl>
  );
}

// Shared layout for every action family: capability and timing first, then
// the costs that apply to the action.
function ActionDetailFields({ fields, costs }: Props) {
  return (
    <div className="action-detail">
      <FieldList fields={fields} />
      {costs && costs.length > 0 && (
        <>
          <h4 className="action-detail-subhead">{WORKSPACE_COPY.actionCostsTitle}</h4>
          <FieldList fields={costs} label={WORKSPACE_COPY.actionCostsTitle} />
        </>
      )}
    </div>
  );
}

export default ActionDetailFields;
