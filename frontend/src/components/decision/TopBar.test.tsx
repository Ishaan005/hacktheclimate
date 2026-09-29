import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SOURCE_KIND_LABEL } from '../../decision/copy/shared';
import { TOP_BAR_COPY } from '../../decision/copy/topBar';
import { fixtureAssessment } from '../../decision/fixture';
import { DEMO_SITES } from '../../decision/sites';
import type { DataSourceKind } from '../../decision/types';
import SourceBadge from './SourceBadge';
import TopBar from './TopBar';

describe('top bar', () => {
  it('switches between the national and site views', () => {
    const onViewChange = vi.fn();
    const { rerender } = render(
      <TopBar context={null} view="national" siteId={null} validated={false} onViewChange={onViewChange} />,
    );
    fireEvent.click(screen.getByRole('radio', { name: TOP_BAR_COPY.viewLabel.site }));
    expect(onViewChange).toHaveBeenLastCalledWith('site', DEMO_SITES[0].id);

    rerender(
      <TopBar context={null} view="site" siteId={DEMO_SITES[0].id} validated={false} onViewChange={onViewChange} />,
    );
    fireEvent.change(screen.getByLabelText(TOP_BAR_COPY.siteLabel), { target: { value: DEMO_SITES[1].id } });
    expect(onViewChange).toHaveBeenLastCalledWith('site', DEMO_SITES[1].id);

    fireEvent.click(screen.getByRole('radio', { name: TOP_BAR_COPY.viewLabel.national }));
    expect(onViewChange).toHaveBeenLastCalledWith('national', null);
  });

  it('shows placeholders before an assessment', () => {
    render(<TopBar context={null} view="national" siteId={null} validated={false} onViewChange={vi.fn()} />);
    expect(screen.getAllByText(TOP_BAR_COPY.noAssessment)).toHaveLength(4);
    expect(screen.getByText(TOP_BAR_COPY.allIsland)).toBeInTheDocument();
  });

  it('shows the site connection and limiting route in site view', () => {
    const site = DEMO_SITES[0];
    render(<TopBar context={null} view="site" siteId={site.id} validated={false} onViewChange={vi.fn()} />);
    expect(screen.getByText(site.connection)).toBeInTheDocument();
    expect(screen.getByText(site.limitingRoute)).toBeInTheDocument();
  });

  it('keeps the view toggle and the status fields in one band, with no spacer', () => {
    const { container } = render(
      <TopBar context={fixtureAssessment.context} view="national" siteId={null} validated={false} onViewChange={vi.fn()} />,
    );
    const toggle = screen.getByRole('group', { name: TOP_BAR_COPY.viewLegend });
    const fields = screen.getByText(TOP_BAR_COPY.window).closest('dl') as HTMLElement;
    expect(toggle.parentElement).toBe(fields.parentElement);
    // Nothing else in the header: no empty row under the toggle.
    const header = container.firstElementChild as HTMLElement;
    expect(header.children).toHaveLength(1);
    // View hints are descriptions, not visible text lines.
    expect(screen.getByRole('radio', { name: TOP_BAR_COPY.viewLabel.national })).toHaveAccessibleDescription(TOP_BAR_COPY.viewHint.national);
  });

  it('labels the fixture as a historical demonstration, never live', () => {
    const { container } = render(
      <TopBar
        context={fixtureAssessment.context}
        view="national"
        siteId={null}
        validated={fixtureAssessment.validated}
        onViewChange={vi.fn()}
      />,
    );
    const badge = container.querySelector('.source-badge');
    expect(badge).toHaveTextContent(SOURCE_KIND_LABEL.historical_demo);
    expect(badge?.textContent).not.toMatch(/live/i);
    expect(within(container).queryByText(/^Live/)).toBeNull();
  });
});

describe('source badge', () => {
  it('never reads Live for a historical demonstration, validated or not', () => {
    for (const validated of [false, true]) {
      const { container, unmount } = render(<SourceBadge kind="historical_demo" validated={validated} />);
      expect(container.textContent).toBe(SOURCE_KIND_LABEL.historical_demo);
      expect(container.textContent).not.toMatch(/live/i);
      expect(container.firstElementChild).not.toHaveClass('source-badge-live');
      unmount();
    }
  });

  it('shows live but not validated differently from validated live', () => {
    const validated = render(<SourceBadge kind="live" validated />);
    const validatedBadge = validated.container.firstElementChild as HTMLElement;
    const validatedText = validatedBadge.textContent;
    const validatedClass = validatedBadge.className;
    validated.unmount();

    const { container } = render(<SourceBadge kind="live" validated={false} />);
    const badge = container.firstElementChild as HTMLElement;
    expect(validatedText).toBe(SOURCE_KIND_LABEL.live);
    expect(badge).toHaveTextContent(TOP_BAR_COPY.liveFeed);
    expect(badge.textContent).not.toBe(validatedText);
    expect(badge.className).not.toBe(validatedClass);
    expect(badge).not.toHaveClass('source-badge-live');
  });

  it('gives each non-live source its own style', () => {
    const kinds: DataSourceKind[] = ['historical_demo', 'planning_case', 'no_live_connection'];
    const classes = kinds.map((kind) => {
      const { container, unmount } = render(<SourceBadge kind={kind} validated />);
      const badge = container.firstElementChild as HTMLElement;
      expect(badge).toHaveTextContent(SOURCE_KIND_LABEL[kind]);
      expect(badge).not.toHaveClass('source-badge-live');
      const className = badge.className;
      unmount();
      return className;
    });
    expect(new Set(classes).size).toBe(kinds.length);
  });
});
