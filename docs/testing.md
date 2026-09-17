# Testing

R3 tests cover R2 gating, typed/serializable quality reports, invalid survival targets, duplicate identifiers, mapping and split contamination, clinical schema/Unknown handling, genomic feature/value/variance checks, subtype/NC policy, deterministic aggregate output, quality-cache refresh, aggregate-only rendering, and prior R1/R2 shell/configuration contracts.

Obsolete tests for the superseded domain were removed with their production modules. Test count is not used as a success metric.

Run (the semantic preparation test needs the optional `data-preparation` dependencies):

```powershell
python -m pip install -e ".[dev,data-preparation]"
python -m pytest -q
python -m compileall -q app.py src tests
python -m compileall -q app.py src scripts tests
python -m pip check
```
