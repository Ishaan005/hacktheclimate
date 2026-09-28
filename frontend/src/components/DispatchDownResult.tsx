import { useState } from 'react';
import DispatchDownCard from './DispatchDownCard';
import DispatchDownChart from './DispatchDownChart';
import './DispatchDown.css';

// Solver output for a dispatch-down risk question: the next-hour estimate and
// the day around it, kept in step when the operator changes the time.
function DispatchDownResult({ target }: { target: string }) {
  const [current, setCurrent] = useState(target);
  return (
    <div className="dd-result">
      <DispatchDownCard initialTarget={target} onTargetChange={setCurrent} />
      <DispatchDownChart target={current} />
    </div>
  );
}

export default DispatchDownResult;
