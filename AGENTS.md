# Repository guide for coding agents

- Start with [README.md](README.md) for the current app and commands; use [docs/README.md](docs/README.md) to find detailed evidence and runbooks.
- Use Python 3.11. Run `python -m pytest -q` for backend changes. For UI changes, run `npm test`, `npm run lint`, and `npm run build` from `frontend/`.
- Preserve processed datasets, trained artifacts, source manifests and audit reports. Original workbooks and raw downloads belong outside Git or under ignored `data/raw/`.
- A forward forecast may use only inputs available at its decision time. Same-period grid measurements belong to retrospective nowcasts. Keep constraint, curtailment and total dispatch-down separate.
- The GFS national model is experimental; August expected-MWh error did not beat zero. Network, safety and avoided-energy claims require their own reviewed inputs and evidence.
