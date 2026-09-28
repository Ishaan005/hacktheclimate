# Forward-Looking National Constraint Forecast

This document details the first forward-looking national constraint forecast model for the Irish power system, keeping `constraint_mwh` strictly separate from system-wide `curtailment_mwh`.

## 1. Target Definition and Separation

In EirGrid and SONI operational reporting, total dispatch-down is the sum of two distinct physical phenomena:
$$\text{dispatch\_down\_total\_mwh} = \text{constraint\_mwh} + \text{curtailment\_mwh}$$

| Target | Physical Driver | Scope | Resolution & Policy |
| --- | --- | --- | --- |
| **`constraint_mwh`** | Local transmission bottlenecks, thermal line limits, voltage stability, and TSO testing | Locational / Network corridor | Relieved only by spatial redispatch or assets sited behind the specific network constraint |
| **`curtailment_mwh`** | System-wide stability constraints (SNSP ceiling, high frequency, RoCoF / minimum system inertia) | System-wide / Non-locational | Relieved by increasing aggregate demand anywhere or raising system operational limits |

This model forecasts **`constraint_mwh`** exclusively. System curtailment is tracked as a prior historical input at decision time, but is never merged into the target.

### Event Definition
A material constraint event is defined as:
$$\text{constraint\_event} = \mathbb{I}(\text{constraint\_mwh} > 5.0\text{ MWh})$$
(corresponding to an average transmission constraint reduction of at least 10 MW over a 30-minute interval).

---

## 2. Forecast-Safe Feature Engineering & Horizon Alignment

For a target period $T_{\text{target}}$ at operational lead time $H$ hours:
- Forecast decision time is $t_0 = T_{\text{target}} - H$.
- **No post-decision features**: All grid measurements are strictly sampled at or before $t_0$.
- **Calendar features**: Only deterministic astronomical/calendar features (hour sin/cos, day-of-week sin/cos, month sin/cos, is_weekend) are evaluated at $T_{\text{target}}$.
- **Historical dynamics**: Deltas ($1\text{h}, 4\text{h}, 24\text{h}$) and rolling statistics ($6\text{h}, 24\text{h}$ means, $24\text{h}$ max) are computed strictly looking backward from $t_0$.
- **Chronological holdout partitioning**: Training and test sets are split on $T_{\text{target}}$, ensuring that no training label or feature incorporates information from the holdout window.

---

## 3. Modeling Architecture

A two-part hurdle model combined with quantile regression intervals:
1. **Event Probability Classifier**: `HistGradientBoostingClassifier` estimating $\hat{p} = \mathbb{P}(\text{constraint\_mwh} > 5.0 \mid X_{t_0})$.
2. **Non-negative Conditional Volume Regressor**: `HistGradientBoostingRegressor` trained strictly on positive constraint events ($\text{constraint\_mwh} > 5.0$), with predictions bounded at zero: $\hat{y}_{\text{vol}} = \max(0, \hat{f}(X_{t_0}))$.
3. **Expected Constraint Volume**:
   $$\hat{y}_{\text{expected}} = \hat{p} \times \hat{y}_{\text{vol}}$$
4. **Calibrated Uncertainty Intervals**: `HistGradientBoostingRegressor(loss='quantile')` fitted at $q \in \{0.05, 0.10, 0.90, 0.95\}$ to produce nominal 80% ($[P_{10}, P_{90}]$) and 90% ($[P_{05}, P_{95}]$) non-negative prediction intervals.

---

## 4. Multi-Horizon Expanding Backtest Results

The model was evaluated across 5 monthly chronological holdouts (April, May, June, July, August 2026), expanding the training history from January 1 up to each test month.

### Aggregate Performance Across Horizons

| Lead Time | Mean Event Prevalence | Mean Event PR-AUC | Calendar/Lag Baseline PR-AUC | Model Expected MAE (MWh) | Calendar/Lag Baseline MAE | Zero Baseline MAE | 80% Empirical Coverage | 90% Empirical Coverage | Outcome Assessment |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| **1 hour** | 0.500 | **0.9727** | 0.9658 | **17.00** | 17.69 | 63.32 | **90.5%** | **94.3%** | Clear improvement, high skill |
| **4 hours** | 0.500 | **0.9123** | 0.8744 | **39.72** | 44.62 | 63.32 | **84.1%** | **89.7%** | Clear improvement, robust lift |
| **12 hours** | 0.500 | **0.7372** | 0.7194 | **67.83** | 70.38 | 63.32 | **86.4%** | **90.5%** | **No improvement** over zero baseline |
| **24 hours** | 0.500 | **0.7021** | 0.6928 | **69.67** | 76.75 | 63.32 | **86.1%** | **89.5%** | **No improvement** over zero baseline |

---

## 5. Detailed Monthly Breakdown

### 1-Hour-Ahead Operational Forecast ($H = 1\text{h}$)
*High operational skill; 73.2% error reduction compared to zero baseline.*

| Test Month | Prevalence | PR-AUC | ECE | Brier Score | Model MAE (MWh) | Cal/Lag MAE | Zero MAE | 80% Interval Cov. | 90% Interval Cov. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **2026-04** | 0.485 | 0.978 | 0.019 | 0.057 | 17.2 | 19.5 | 79.7 | 89.2% | 91.2% |
| **2026-05** | 0.536 | 0.969 | 0.111 | 0.104 | 28.1 | 27.5 | 82.3 | 86.3% | 91.7% |
| **2026-06** | 0.619 | 0.978 | 0.032 | 0.074 | 19.9 | 20.4 | 84.2 | 88.1% | 92.4% |
| **2026-07** | 0.568 | 0.985 | 0.023 | 0.053 | 13.6 | 14.2 | 55.4 | 92.2% | 97.0% |
| **2026-08** | 0.292 | 0.953 | 0.029 | 0.055 | 6.1 | 6.8 | 15.0 | 96.6% | 99.0% |

### 4-Hours-Ahead Intraday Forecast ($H = 4\text{h}$)
*Maintains actionable intraday skill; 37.3% error reduction over zero baseline, 11.0% lift over calendar/lag baseline.*

| Test Month | Prevalence | PR-AUC | ECE | Brier Score | Model MAE (MWh) | Cal/Lag MAE | Zero MAE | 80% Interval Cov. | 90% Interval Cov. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **2026-04** | 0.485 | 0.919 | 0.054 | 0.111 | 53.7 | 54.8 | 79.7 | 80.3% | 85.6% |
| **2026-05** | 0.536 | 0.927 | 0.249 | 0.211 | 50.3 | 58.3 | 82.3 | 74.5% | 84.5% |
| **2026-06** | 0.619 | 0.933 | 0.053 | 0.126 | 49.0 | 53.2 | 84.2 | 82.4% | 88.9% |
| **2026-07** | 0.568 | 0.933 | 0.031 | 0.121 | 31.3 | 38.4 | 55.4 | 86.0% | 91.5% |
| **2026-08** | 0.292 | 0.850 | 0.037 | 0.099 | 14.3 | 18.4 | 15.0 | 97.3% | 98.3% |

### 12-Hours and 24-Hours Ahead ($H = 12\text{h}, 24\text{h}$)
*Honest assessment: Horizon degradation without Numerical Weather Prediction (NWP) inputs.*

- At **12h**, PR-AUC falls to **0.7372**, and Model MAE (67.83 MWh) exceeds the simple zero-prediction baseline (63.32 MWh).
- At **24h**, PR-AUC falls to **0.7021** (in April 2026 it falls to **0.490**, roughly equal to event prevalence 0.485). Model MAE (69.67 MWh) fails to beat the zero baseline (63.32 MWh).
- **Physical Root Cause**: Transmission constraints are driven by high renewable generation (especially onshore wind in the West/South-West) coinciding with transmission transfer limits. At lead times beyond 4–8 hours, system state measurements taken 12 to 24 hours prior lose predictive correlation with future wind and line loading. Weather systems move, wind ramps develop or abate, and historical grid lags decay into noise.
- **Defensible Conclusion**: A day-ahead (24h) national constraint forecast based solely on historical grid lags cannot beat naive baselines. A true day-ahead product strictly requires point-in-time Numerical Weather Prediction (NWP) wind speed/direction and demand forecasts.

---

## 6. Probability Calibration and Uncertainty Coverage

- **Probability Calibration**:
  - For $H = 1\text{h}$, Expected Calibration Error (ECE) is low (mean $0.043$), with Brier scores around $0.069$.
  - For $H = 24\text{h}$, ECE rises to $0.191$ and Brier score to $0.262$, reflecting heightened predictive uncertainty.
- **Uncertainty Interval Coverage**:
  - The non-negative quantile intervals $[P_{10}, P_{90}]$ achieve **84.1%–90.5%** empirical coverage across horizons, meeting or exceeding the nominal 80% target.
  - The nominal 90% intervals $[P_{05}, P_{95}]$ achieve **89.5%–94.3%** empirical coverage across all tested horizons.

---

## 7. Explicit Non-Claims and Operational Boundaries

> [!CAUTION]
> **No Location Claim**: Transmission constraints arise from physical transmission network limitations (e.g. line thermal ratings, voltage stability, transformer capacity). This model predicts only aggregate national MWh and probability. It does NOT identify which circuit, bus, or region will experience a constraint.

> [!WARNING]
> **No Avoided-Energy Claim**: Demonstrating that national constraint MWh was predicted does NOT mean that an arbitrary battery or EV fleet elsewhere on the island could absorb it. Siting flexible load on the wrong side of a transmission constraint can exacerbate, rather than relieve, network congestion. A valid avoided-curtailment or avoided-constraint claim requires power-flow nodal feasibility.

---

## 8. Saved Artifacts and Verification

Artifacts are saved in `artifacts/forward_constraint/` without overwriting retrospective demo files:
- `artifacts/forward_constraint/model_1h.joblib`
- `artifacts/forward_constraint/model_4h.joblib`
- `artifacts/forward_constraint/model_12h.joblib`
- `artifacts/forward_constraint/model_24h.joblib`
- `artifacts/forward_constraint/metrics.json`
- `artifacts/forward_constraint/metadata.json`

To reproduce the multi-horizon backtest:
```bash
python scripts/backtest_forward_constraint.py --horizons 1,4,12,24
```
To run automated tests:
```bash
pytest tests/test_forward_constraint.py -v
```
