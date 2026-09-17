# Testing

R1 tests cover domain-neutral environment parsing, biomedical pending-result construction and serialization, invalid contract values, approved navigation order, responsive/accessibility CSS, safe escaped rendering, biomedical branding, pending states, unresolved subtype taxonomy, persistent disclaimer, and Streamlit page dispatch.

Obsolete tests for the superseded domain were removed with their production modules. Test count is not used as a success metric.

Run:

```powershell
pytest -q
python -m compileall -q app.py src tests
python -m pip check
```
