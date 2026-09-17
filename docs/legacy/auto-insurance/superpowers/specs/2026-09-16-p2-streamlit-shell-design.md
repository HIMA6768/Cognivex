# P2 Streamlit Shell and Visual Design System

## Goal

Create a polished, responsive Streamlit application shell for the pre-model
vehicle-damage assessment prototype. P2 establishes navigation, visual tokens,
shared layout components, and safe page placeholders without implementing
upload, validation, inference, decisioning, or model metrics.

## Experience

The application should feel like a lightweight insurance product rather than a
default Streamlit tutorial. A deep navy sidebar provides product identity and
navigation. The main canvas uses a pale neutral background, white surfaces,
restrained blue accents, subtle borders, generous spacing, and readable type.
Status is communicated with text and shape as well as color.

The persistent shell contains:

- Product name: Auto Insurance Damage Assessment
- Subtitle: AI-assisted vehicle damage triage
- Prototype status
- Five navigation destinations: Assessment, Model Comparison, Model Insights,
  Monitoring, and System / About
- Decision-support disclaimer

## Architecture

`app.py` is a thin Streamlit entrypoint. It configures the page and delegates to
`src/ui/shell.py`. The shell applies `src/ui/theme.py`, renders navigation from
typed metadata in `src/ui/navigation.py`, and dispatches to page renderers.
Reusable page headers and empty states live in `src/ui/components/layout.py`.
No page accesses model runtimes, files, or external services.

## Navigation contract

Navigation order is stable:

1. Assessment
2. Model Comparison
3. Model Insights
4. Monitoring
5. System / About

The sidebar uses a single selection widget with an accessible label. Page
metadata provides the display label and renderer key; selection state remains
stable across ordinary Streamlit reruns.

## Page scope

- Assessment: orientation content and six-stage workflow preview only. Upload is
  explicitly deferred to P3.
- Model Comparison: polished pending state; no invented metrics or charts.
- Model Insights: polished unavailable state; no invented analysis.
- Monitoring: zero-data development state; no fabricated traffic.
- System / About: architecture flow, model families under evaluation, known
  limitations, and decision-support disclaimer.

## Visual tokens

- Navy: `#0B1F33`
- Slate: `#344054`
- Text: `#101828`
- Muted text: `#667085`
- Blue accent: `#2563EB`
- Canvas: `#F5F7FA`
- Surface: `#FFFFFF`
- Border: `#DDE3EA`
- Success: `#16794B`
- Amber: `#B54708`
- Border radius: 14px for cards, 10px for compact controls
- Responsive breakpoint: 768px

## Accessibility and responsive behavior

- Navigation and controls retain readable labels.
- Focus states remain visible.
- Color is never the only status signal.
- Content columns stack below 768px.
- Fixed widths that could overflow mobile are prohibited.
- Empty states explain what is missing and what happens next.

## Test strategy

- Pure tests verify page order, labels, metadata, visual tokens, responsive CSS,
  and renderer registration.
- Streamlit AppTest verifies the app starts without exceptions and exposes the
  expected shell/navigation content.
- A live local server is visually checked in a browser for content, navigation,
  console/runtime errors, and responsive layout.

## Out of scope

- File upload and image preview
- Image validation or quality analysis
- Mock or real model inference
- Result cards and localization overlays
- Decision engine behavior
- External credentials or service integrations
- Model metrics, charts, or production claims
