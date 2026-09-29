import { WORKSPACE_COPY } from '../copy';

export type DetailField = {
  label: string;
  value: string;
  // Mono for timestamps and technical values that line up across rows.
  mono?: boolean;
};

// Which half to render: capability and timing, or costs. The action
// carousel shows each half on its own slide.
export type DetailPart = 'fields' | 'costs';

type Props = {
  fields: DetailField[];
  costs?: DetailField[];
  part: DetailPart;
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

// Shared layout for every action family.
function ActionDetailFields({ fields, costs, part }: Props) {
  if (part === 'fields') {
    return (
      <div className="action-detail">
        <FieldList fields={fields} />
      </div>
    );
  }
  return (
    <div className="action-detail">
      {costs && costs.length > 0 ? (
        <FieldList fields={costs} label={WORKSPACE_COPY.actionCostsTitle} />
      ) : (
        <p className="action-detail-empty">{WORKSPACE_COPY.actionCostsNone}</p>
      )}
    </div>
  );
}

export default ActionDetailFields;
