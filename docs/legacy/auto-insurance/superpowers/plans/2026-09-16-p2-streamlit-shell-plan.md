# P2 Streamlit Shell and Visual Design System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify a polished Streamlit shell, visual system, navigation, and pre-model page placeholders.

**Architecture:** `app.py` delegates to a reusable UI shell. Theme CSS, navigation metadata, layout components, and page renderers remain in focused modules under `src/ui/`. Pages contain presentation only and never access model runtimes or external services.

**Tech Stack:** Python 3.11+, Streamlit 1.39+, pytest, Streamlit AppTest, CSS injected from trusted static source.

**Spec:** `docs/superpowers/specs/2026-09-16-p2-streamlit-shell-design.md`

## Global Constraints

- Use Streamlit; do not introduce Next.js or React.
- Keep model and decision logic out of Streamlit widgets.
- Do not implement file upload, validation, inference, or result behavior in P2.
- Do not invent metrics, traffic, confidence values, or model results.
- Preserve the existing configuration contracts and unrelated root `env.example`.
- Use restrained navy/slate/blue styling, responsive layouts, visible focus, and text labels for status.
- Update tests and documentation before the increment gate.

---

### Task 1: Theme, navigation, and reusable layout foundation

**Files:**
- Create: `src/ui/__init__.py`
- Create: `src/ui/theme.py`
- Create: `src/ui/navigation.py`
- Create: `src/ui/components/__init__.py`
- Create: `src/ui/components/layout.py`
- Test: `tests/test_ui_foundation.py`

**Interfaces:**
- Produce `APP_CSS`, `apply_theme()`, `Page`, `PageSpec`, `PAGE_SPECS`, `PAGE_ORDER`, `render_navigation()`, `render_page_header()`, `render_empty_state()`, and `render_shell_status()`.
- Page order and display labels must match the design spec exactly.

- [ ] Write focused tests first for navigation order/labels, unique renderer keys, required CSS tokens, the 768px responsive breakpoint, visible focus styling, and trusted layout HTML.
- [ ] Run `pytest tests/test_ui_foundation.py -v` and verify failure because UI modules do not exist.
- [ ] Implement the minimum static theme, metadata, and layout helpers required by the tests.
- [ ] Run the focused test and then `pytest -q`.
- [ ] Self-review for unsafe dynamic HTML, inaccessible labels, excessive styling, and accidental application logic.

### Task 2: Application shell and page placeholders

**Files:**
- Create: `app.py`
- Create: `.streamlit/config.toml`
- Create: `src/ui/shell.py`
- Create: `src/ui/pages/__init__.py`
- Create: `src/ui/pages/assessment.py`
- Create: `src/ui/pages/model_comparison.py`
- Create: `src/ui/pages/model_insights.py`
- Create: `src/ui/pages/monitoring.py`
- Create: `src/ui/pages/system_about.py`
- Test: `tests/test_app_shell.py`

**Interfaces:**
- Consume Task 1 theme/navigation/layout contracts.
- Produce `PAGE_RENDERERS` and `render_app()`; `app.py` must only call `render_app()`.

- [ ] Install declared runtime dependencies into the existing ignored virtual environment if needed.
- [ ] Write Streamlit AppTest tests first for clean startup, five navigation labels, product heading/subtitle, prototype indicator, persistent disclaimer, and exact pending-data copy.
- [ ] Run `pytest tests/test_app_shell.py -v` and verify expected failure before implementing the shell.
- [ ] Implement the thin entrypoint, Streamlit page configuration, shell, page registry, and five scoped placeholders.
- [ ] Run focused tests and `pytest -q`.
- [ ] Start Streamlit locally and record the server URL/logs for parent visual verification.
- [ ] Self-review session-state behavior, duplicate widget keys, page dispatch, empty/error states, and scope boundaries.

### Task 3: Documentation

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture.md`
- Modify: `docs/setup.md`
- Modify: `docs/limitations.md`
- Modify: `docs/implementation_log.md`
- Create: `docs/ui_design.md`
- Create: `docs/user_flow.md`

**Interfaces:**
- Document only the verified Task 1–2 implementation and exact run/test commands.

- [ ] Update current-state, startup, architecture, visual-system, navigation, accessibility, and deferred-feature documentation.
- [ ] Verify every documented path and command exists.
- [ ] Confirm no documentation claims upload, inference, metrics, or production readiness.

### Task 4: Parent integration and visual verification

**Files:**
- Verify all P2 files and unchanged P1 contracts.

- [ ] Inspect the complete P2 file set and child reports.
- [ ] Run the full test suite, compile/import smoke checks, and secret/scope scans.
- [ ] Start the Streamlit server and verify the live page in a browser.
- [ ] Exercise all five navigation destinations and inspect the mobile-width layout.
- [ ] Dispatch a final whole-increment review and resolve blocking findings.
- [ ] Record the P2 gate status, risks, AI-handoff dependencies, and exactly one next increment.
