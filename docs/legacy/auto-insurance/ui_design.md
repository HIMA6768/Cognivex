# UI design

## Visual direction

P2 uses a restrained insurtech visual system rather than default Streamlit styling. The persistent shell pairs a deep navy sidebar with a pale neutral canvas and white content surfaces. The static tokens are owned by `src/ui/theme.py`:

- Navy `#0B1F33` for product identity and sidebar.
- Slate `#344054`, dark text `#101828`, and muted text `#667085` for hierarchy.
- Blue `#2563EB` for focus and primary accent.
- Canvas `#F5F7FA`, surface `#FFFFFF`, and border `#DDE3EA` for readable page structure.
- Green and amber are reserved status colors; status also uses text and shape.

Cards use a 14px radius; compact controls use a 10px radius. The system is intentionally quiet: no fabricated charts, traffic, confidence values, or model outcomes are shown.

## Shell and navigation

The navy sidebar contains the product name, the subtitle “AI-assisted vehicle damage triage,” a high-contrast “Prototype status: pre-model” indicator, and a single labelled navigation control. The stable order is Assessment, Model Comparison, Model Insights, Monitoring, and System / About.

Each destination uses a consistent page header. Empty states are white bordered surfaces that state what is unavailable and what must happen next. A decision-support disclaimer is present after every page renderer.

## Assessment upload experience

The Assessment page uses Streamlit's labelled drag-and-drop uploader inside the existing neutral canvas. It states the allowed JPG/JPEG, PNG, and WEBP formats, the configured maximum size, and four practical photo tips before a file is selected. An accepted image appears in a bordered preview surface with a primary Analyze Damage action and a secondary Upload another image action.

Analyze Damage is visibly a safe placeholder: it confirms P4 and P5 acceptance but does not render a prediction. Invalid uploads show corrective text and an upload-another action. The selected image persists only for the current Streamlit session, so ordinary widget reruns do not discard it.

## Structural validation feedback

P4 keeps invalid uploads inside the same calm, actionable Assessment experience. The page shows a user-safe corrective message for an unsupported, malformed, oversized, animated, undersized, or overly large image and never exposes a parser traceback. After success, the preview uses EXIF-oriented RGB or RGBA PNG bytes so grayscale and transparent images remain visually predictable. This is structural safety only, not a quality score.

## Quality-gate feedback

P5 keeps the P4 preview visible and shows an actionable message for every failed deterministic blur, darkness, or brightness check. It does not surface raw measurement values as primary copy. Analyze Damage becomes disabled while the report fails, and Upload another image remains available. This is a usability gate only; it does not create a resubmission route, claim disposition, or prediction.

## Responsive and accessible behavior

The layout uses Streamlit's automatic sidebar behavior and sets the initial sidebar state to `auto`. At widths below 768px, horizontal content blocks stack to full width and page padding becomes more compact. Sidebar collapse and expand controls receive scoped high-contrast styling.

Keyboard focus is visible on interactive controls and links. Navigation remains text-labelled, and the prototype status uses a dot, pill shape, and explicit wording rather than color alone. Dynamic empty-state text is HTML-escaped before the trusted layout markup is rendered.

## Deliberate scope boundary

P5 contains no model-derived quality score, resubmission recommendation, inference result, localization overlay, routing recommendation, metrics, chart, or production claim. Pending AI model handoff.
