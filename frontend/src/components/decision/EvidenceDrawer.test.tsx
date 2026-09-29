import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { fixtureAssessment } from '../../decision/fixture';
import EvidenceDrawer from './EvidenceDrawer';

const { evidence, edits, validated, context } = fixtureAssessment;

function renderDrawer() {
  return render(<EvidenceDrawer evidence={evidence} edits={edits} validated={validated} sourceKind={context.sourceKind} />);
}

describe('EvidenceDrawer', () => {
  it('is closed by default', () => {
    renderDrawer();
    const details = screen.getByText('Show the evidence').closest('details') as HTMLDetailsElement;
    expect(details).not.toHaveAttribute('open');
    expect(screen.getByText('Show the evidence')).toHaveClass('panel-title');
  });

  it('lists the audit ID, rule version and why an action was rejected', () => {
    renderDrawer();
    expect(screen.getByText('demo-0001')).toBeInTheDocument();
    expect(screen.getByText('demo-policy-v1 (not EirGrid/SONI confirmed)')).toBeInTheDocument();
    const rejected = screen.getByText('No protection or fault-current study for the switching sequence.').closest('li') as HTMLElement;
    expect(rejected).toHaveTextContent('Rejected');
    expect(rejected).toHaveTextContent('Switch or sectionalise the network');
  });

  it('flags operator-edited inputs, feed freshness and demonstration status', () => {
    renderDrawer();
    const failureRow = screen.getByRole('rowheader', { name: 'Credible failure set' }).closest('tr') as HTMLElement;
    expect(failureRow).toHaveTextContent('Edited by operator');
    expect(screen.getByText('SCADA', { exact: false }).closest('li')).toHaveTextContent('Missing');
    expect(screen.getByText('Historical demonstration')).toBeInTheDocument();
    expect(screen.queryByText(/validated/i)).toBeNull();
    expect(screen.getByText('No operator edits.')).toBeInTheDocument();
  });
});
