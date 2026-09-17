"""Contracts for the static Streamlit UI foundation."""

from __future__ import annotations


class _ThemeRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, bool]] = []

    def markdown(self, body: str, *, unsafe_allow_html: bool) -> None:
        self.calls.append(("markdown", body, unsafe_allow_html))


class _SidebarRecorder:
    def __init__(self, selected) -> None:
        self.selected = selected
        self.calls: list[dict[str, object]] = []

    def radio(self, label, options, *, format_func, key) -> object:
        self.calls.append(
            {
                "label": label,
                "options": tuple(options),
                "labels": tuple(format_func(option) for option in options),
                "key": key,
            }
        )
        return self.selected


class _StreamlitRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def markdown(self, body: str, *, unsafe_allow_html: bool) -> None:
        self.calls.append(("markdown", body, unsafe_allow_html))

    def title(self, body: str) -> None:
        self.calls.append(("title", body))

    def caption(self, body: str) -> None:
        self.calls.append(("caption", body))

    def subheader(self, body: str) -> None:
        self.calls.append(("subheader", body))

    def write(self, body: str) -> None:
        self.calls.append(("write", body))

    def info(self, body: str) -> None:
        self.calls.append(("info", body))


def test_page_specs_preserve_the_designed_navigation_order_and_labels() -> None:
    """Changing a destination's order or customer label breaks stable navigation."""
    from src.ui.navigation import PAGE_ORDER, PAGE_SPECS, Page

    assert PAGE_ORDER == (
        Page.ASSESSMENT,
        Page.MODEL_COMPARISON,
        Page.MODEL_INSIGHTS,
        Page.MONITORING,
        Page.SYSTEM_ABOUT,
    )
    assert [PAGE_SPECS[page].label for page in PAGE_ORDER] == [
        "Assessment",
        "Model Comparison",
        "Model Insights",
        "Monitoring",
        "System / About",
    ]


def test_page_specs_map_each_page_to_its_renderer_key() -> None:
    """A wrong renderer key would dispatch a destination to the wrong page implementation."""
    from src.ui.navigation import PAGE_SPECS, Page

    assert {page: spec.renderer_key for page, spec in PAGE_SPECS.items()} == {
        Page.ASSESSMENT: "assessment",
        Page.MODEL_COMPARISON: "model_comparison",
        Page.MODEL_INSIGHTS: "model_insights",
        Page.MONITORING: "monitoring",
        Page.SYSTEM_ABOUT: "system_about",
    }


def test_app_css_supplies_design_tokens_responsive_stacking_and_focus_visibility() -> None:
    """Removing a token, focus ring, or mobile rule would make the shell inaccessible or off-brand."""
    from src.ui.theme import APP_CSS

    for token in (
        "#0B1F33",
        "#344054",
        "#101828",
        "#667085",
        "#2563EB",
        "#F5F7FA",
        "#FFFFFF",
        "#DDE3EA",
        "#16794B",
        "#B54708",
        "14px",
        "10px",
    ):
        assert token in APP_CSS

    assert "@media (max-width: 768px)" in APP_CSS
    assert ".stHorizontalBlock" in APP_CSS
    assert "flex-direction: column" in APP_CSS
    assert ":focus-visible" in APP_CSS
    assert "outline" in APP_CSS
    assert '[data-testid="stVerticalBlockBorderWrapper"]' not in APP_CSS
    assert '[data-testid="stSidebar"] *' not in APP_CSS
    assert '[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] > p' not in APP_CSS
    assert ".cv-sidebar-brand" in APP_CSS
    assert ".cv-sidebar-brand *" in APP_CSS
    assert '[data-testid="stSidebar"] [role="radiogroup"] label:has(input:not(:disabled))' in APP_CSS
    assert ".cv-status-pill" in APP_CSS
    assert "background: #155F3A" in APP_CSS
    assert "color: #FFFFFF" in APP_CSS
    assert ".cv-surface" in APP_CSS
    assert "padding: 1.5rem" in APP_CSS
    assert '[data-testid="stSidebar"][aria-expanded="true"]' in APP_CSS
    assert '[data-testid="stSidebar"][aria-expanded="false"]' in APP_CSS
    assert '[data-testid="stExpandSidebarButton"]' in APP_CSS


def test_app_css_forces_mobile_streamlit_columns_to_full_width() -> None:
    """A parent-only mobile rule leaves child columns at their desktop widths."""
    from src.ui.theme import APP_CSS

    mobile_column_rule = '''[data-testid="stHorizontalBlock"].stHorizontalBlock > [data-testid="stColumn"] {
        width: 100% !important;
        min-width: 100% !important;
        flex-basis: 100% !important;
    }'''

    assert "@media (max-width: 768px)" in APP_CSS
    assert mobile_column_rule in APP_CSS


def test_apply_theme_injects_the_trusted_static_stylesheet(monkeypatch) -> None:
    """Theme injection must use the package stylesheet, not caller-provided HTML."""
    from src.ui import theme

    recorder = _ThemeRecorder()
    monkeypatch.setattr(theme, "st", recorder)

    theme.apply_theme()

    assert recorder.calls == [("markdown", f"<style>{theme.APP_CSS}</style>", True)]


def test_navigation_uses_an_accessible_label_and_stable_widget_key(monkeypatch) -> None:
    """A missing label or changing key makes keyboard access and reruns unreliable."""
    from src.ui import navigation
    from src.ui.navigation import PAGE_ORDER, PAGE_SPECS, Page

    sidebar = _SidebarRecorder(Page.MONITORING)
    monkeypatch.setattr(navigation.st, "sidebar", sidebar)

    selected = navigation.render_navigation()

    assert selected is Page.MONITORING
    assert sidebar.calls == [
        {
            "label": "Navigation",
            "options": PAGE_ORDER,
            "labels": tuple(PAGE_SPECS[page].label for page in PAGE_ORDER),
            "key": "primary_navigation",
        }
    ]


def test_layout_helpers_render_headers_and_status_through_streamlit_apis(monkeypatch) -> None:
    """The static status pill must retain its visible text and semantic status role."""
    from src.ui.components import layout

    recorder = _StreamlitRecorder()
    monkeypatch.setattr(layout, "st", recorder)

    layout.render_page_header("Assessment", "Start with a vehicle photo.")
    layout.render_shell_status()

    assert recorder.calls == [
        ("title", "Assessment"),
        ("caption", "Start with a vehicle photo."),
        (
            "markdown",
            '<div class="cv-status-pill" role="status">'
            '<span aria-hidden="true">●</span> Prototype status: pre-model</div>',
            True,
        ),
    ]


def test_empty_state_emits_a_semantic_surface_and_escapes_caller_markup(monkeypatch) -> None:
    """Unescaped empty-state copy would allow markup to escape the reusable surface."""
    from src.ui.components import layout

    recorder = _StreamlitRecorder()
    monkeypatch.setattr(layout, "st", recorder)

    layout.render_empty_state(
        '<script>alert("title")</script>',
        "Unsafe & <strong>message</strong>",
        'Read <a href="/next">the guide</a>',
    )

    assert recorder.calls == [
        (
            "markdown",
            '<section class="cv-surface" role="status">'
            '<h2>&lt;script&gt;alert(&quot;title&quot;)&lt;/script&gt;</h2>'
            '<p>Unsafe &amp; &lt;strong&gt;message&lt;/strong&gt;</p>'
            '<p><strong>Next:</strong> Read &lt;a href=&quot;/next&quot;&gt;the guide&lt;/a&gt;</p>'
            "</section>",
            True,
        )
    ]
