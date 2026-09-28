import { useId } from 'react';
import type { ReactNode } from 'react';

type TermProps = {
  children: ReactNode;
  definition: string;
};

// Dotted-underline term with a plain-language definition. Opens on hover
// and on keyboard focus or tap, and screen readers get it as a description.
function Term({ children, definition }: TermProps) {
  const id = useId();
  return (
    <span className="term" tabIndex={0} aria-describedby={id}>
      {children}
      <span className="term-tip" role="tooltip" id={id}>
        {definition}
      </span>
    </span>
  );
}

export default Term;
