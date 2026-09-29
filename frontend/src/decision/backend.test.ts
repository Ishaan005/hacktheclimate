import { describe, expect, it, vi } from 'vitest';
import { fromBackendAssessment, label, operatorReason, toBackendRequest } from './backend';
import type { BackendAssessment } from './backend';
import type { AssessmentRequest } from './api';

const condition = {
  scenarioId: 'T3' as const, situationKey: 't_outage_overload', reach: null,
  limitingAsset: 'Route A', outageType: 'planned' as const, timeSetting: 'forecast' as const,
  snspDrivers: [], jurisdiction: null, confirmedByOperator: true,
};

function request(): AssessmentRequest {
  return { description: 'route overload in outage', view: 'site', siteId: 'demo-wind-west',
    conditions: [condition], edits: [], facts: [{
      id: 'normal_flow_mw', label: 'Normal route flow', value: 420, unit: 'MW',
      source: 'Operator', timestamp: '2026-09-29T15:00:00Z', origin: 'operator',
      state: 'current', family: 'transmission', conflictNote: null, editable: true, editedFrom: null,
    }], alternative: { id: 'plan-operator', name: 'Operator alternative', origin: 'operator',
      label: 'insufficient_evidence', labelReason: 'Not assessed yet.', steps: [{
        id: 'step-a', kind: 'local_storage_or_demand', role: 'main', instruction: 'Charge Battery A',
        executor: 'Battery A', permissionRoute: 'needs_acceptance', permissionState: 'refused',
        permissionParty: 'owner', startTime: null, effectTime: null, durationMinutes: null,
        mwEffect: -5, dependsOn: [], blockingCheckIds: [],
      }] },
  };
}

const unknownBenefit = { value: null, unit: 'MWh', method: null, source: null, reason: 'Not established' };
const baseline = {
  plan: { steps: [] },
  safety: { status: 'UNKNOWN' as const, reason: 'Missing study', missing_checks: ['credible_failure_flow'] },
  plan_label: 'Insufficient evidence' as const,
  checks: [{ check_id: 'credible_failure_flow', family: 'transmission' as const,
    action_step_id: null, status: 'UNKNOWN' as const, value: null, unit: 'MW',
    effective_limit: null, margin: null, worst_time: null, worst_failure: null,
    source: null, reason: 'No study' }],
  delivered_relief_mw: null, response_time_seconds: null, time_to_breach_seconds: null,
  worst_limit_margin: null, benefits: { constraint_mwh: unknownBenefit, curtailment_mwh: unknownBenefit },
};

function backendResponse(): BackendAssessment {
  return {
    schema_version: 1, case_id: 'case-1', assessed_at: '2026-09-29T15:01:00Z',
    view: 'site', location: 'Demonstration wind farm B (west)', decision_time: '2026-09-29T15:00:00Z',
    window: { starts_at: '2026-09-29T15:30:00Z', ends_at: '2026-09-30T15:30:00Z' },
    source_status: 'no_live_connection', bindings: [{ scenario_id: 'T3', missing_fields: ['credible_failure'] }],
    facts: [{ field: 'normal_flow_mw', family: 'transmission', value: 420, unit: 'MW',
      source: 'Operator', source_type: 'operator', available_at: '2026-09-29T15:00:00Z',
      observed_at: null, issued_at: null, valid_at: null, state: 'current', reason: null,
      observations: [{ value: 420, source: 'Operator' }], operator_edit: true }],
    active_instructions: [],
    comparisons: {
      current_plan: baseline, no_new_instruction: baseline, proposed_plan: baseline,
      operator_alternative: { ...baseline, plan: { steps: [{
        step_id: 'step-a', action_id: 'STORAGE_CHARGE', role: 'main',
        instruction: 'Charge Battery A', asset_or_party: 'Battery A', executor: 'Battery A',
        permission_route: 'needs_acceptance', permission: 'denied', permission_party: 'owner',
        starts_at: null, effect_at: null, ends_at: null,
        limiting_location_delta_mw: -5, depends_on: [],
      }] },
        safety: { status: 'FAIL', reason: 'Permission denied', missing_checks: ['credible_failure_flow'] },
        plan_label: 'Unsafe', checks: [...baseline.checks, { ...baseline.checks[0],
          check_id: 'permission', family: 'action', action_step_id: 'step-a', status: 'FAIL', reason: 'Permission denied' }] },
    },
    evidence: { scenario_catalogue_source: 'issue-47', scenario_catalogue_version: 1,
      safety_policy_version: null, model_version: null, assumptions: [], missing_checks: ['credible_failure_flow'],
      audit_id: 'workspace-123', audit_persisted: false, reason: 'No live operational feed' },
  };
}

describe('backend workspace adapter', () => {
  it('sends locked IDs, operator edits and alternative steps to the real route contract', () => {
    const body = toBackendRequest(request(), new Date('2026-09-29T15:01:00Z'));
    expect(body.decision_case.scenario_ids).toEqual(['T3']);
    expect(body.description).toBe('route overload in outage');
    expect(body.conditions).toEqual([expect.objectContaining({
      scenario_id: 'T3', situation_key: 't_outage_overload',
    })]);
    expect(body.decision_case.starts_at).toBe('2026-09-29T15:30:00.000Z');
    expect(body.decision_case.ends_at).toBe('2026-09-30T15:30:00.000Z');
    expect(body.evidence).toEqual(expect.arrayContaining([
      expect.objectContaining({ field: 'normal_flow_mw', value: 420, source_type: 'operator' }),
    ]));
    expect(body.operator_alternative.steps[0]).toMatchObject({
      action_id: 'STORAGE_CHARGE', role: 'main', instruction: 'Charge Battery A',
      permission_route: 'needs_acceptance', permission: 'denied',
      permission_party: 'owner', limiting_location_delta_mw: -5,
    });
  });

  it('replaces a reviewed field with its operator correction', () => {
    const changed = request();
    changed.facts.push({ ...changed.facts[0], id: 'limiting_equipment', label: 'Limiting equipment',
      value: 'Route B', unit: null });
    const body = toBackendRequest(changed, new Date('2026-09-29T15:01:00Z'));
    expect(body.evidence.filter((item) => item.field === 'limiting_equipment'))
      .toEqual([expect.objectContaining({ value: 'Route B' })]);
  });

  it('renders server safety and unavailable outcomes without claiming live validation', () => {
    const assessment = fromBackendAssessment(backendResponse(), request());
    expect(assessment.context.sourceKind).toBe('no_live_connection');
    expect(assessment.validated).toBe(false);
    expect(assessment.overall.result).toBe('fail');
    expect(assessment.alternative?.label).toBe('unsafe');
    expect(assessment.alternative?.steps[0]).toMatchObject({
      id: 'step-a', kind: 'local_storage_or_demand', instruction: 'Charge Battery A',
      permissionState: 'refused', mwEffect: -5,
    });
    expect(assessment.actionChecks[0].stepId).toBe('step-a');
    expect(assessment.outcomes).toHaveLength(4);
    expect(assessment.outcomes.every((item) => item.windowStart === '2026-09-29T15:30:00Z')).toBe(true);
    expect(assessment.benefits.avoidedDispatchDownMwh.value).toBeNull();
    expect(assessment.evidence.auditId).toBeNull();
  });
});

describe('operator-facing text', () => {
  it('turns backend field IDs into readable labels with units', () => {
    expect(label('demand_mw')).toBe('Demand (MW)');
    expect(label('wind_generation_mw')).toBe('Wind generation (MW)');
    expect(label('all_island_snsp')).toBe('All-island SNSP');
    expect(label('rocof_and_stability')).toBe('RoCoF and stability');
    expect(label('planning_min_generation')).toBe('Planning case: minimum generation');
    expect(label('snsp_ratio_pct')).toBe('All-island SNSP');
  });

  it('keeps file paths and exception text off the screen', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(operatorReason("Planning evaluation unavailable: [Errno 2] No such file or directory: '/Users/x/data.json'"))
      .toBe('Planning-case inputs are not available on this server.');
    expect(operatorReason('Operational assessment is not connected')).toBe('Operational assessment is not connected');
  });
});
