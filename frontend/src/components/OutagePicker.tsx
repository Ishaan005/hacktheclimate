import type { ReviewedOutageOption } from '../types';
import './OutagePicker.css';

type OutagePickerProps = {
  outages: ReviewedOutageOption[];
  selectedId: string | null;
  onSelect: (outageId: string | null) => void;
};

function OutagePicker({ outages, selectedId, onSelect }: OutagePickerProps) {
  return (
    <div className="outage-picker">
      <label htmlFor="outage-select">Reviewed outage</label>
      <select
        className="input"
        id="outage-select"
        value={selectedId ?? ''}
        onChange={(event) => onSelect(event.target.value || null)}
      >
        <option value="">None selected</option>
        {outages.map((item) => (
          <option key={item.outage_id} value={item.outage_id}>
            {item.outage_id}: {item.equipment_description}
          </option>
        ))}
      </select>
    </div>
  );
}

export default OutagePicker;
