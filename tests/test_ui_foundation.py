"""Contracts for the reusable Streamlit UI foundation."""

from __future__ import annotations


class _ThemeRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, bool]] = []

    def markdown(self, body: str, *, unsafe_allow_html: bool) -> None:
        self.calls.append(("markdown", body, unsafe_allow_html))


class _NavigationRecorder:
    def __init__(self) -> None:
        self.sidebar = self
        self.session_state: dict[str, object] = {}
        self.calls: list[dict[str, object]] = []

    def radio(self, label, options, *, index, format_func, key, on_change, args) -> object:
        self.calls.append(
            {
                "label": label,
                "options": tuple(options),
                "labels": tuple(format_func(option) for option in options),
                "key": key,
                "index": index,
            }
        )
        return options[index] if index is not None else None


class _StreamlitRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def markdown(self, body: str, *, unsafe_allow_html: bool) -> None:
        self.calls.append(("markdown", body, unsafe_allow_html))

    def title(self, body: str) -> None:
        self.calls.append(("title", body))

    def caption(self, body: str) -> None:
        self.calls.append(("caption", body))


def test_navigation_preserves_the_approved_oncomap_order() -> None:
    from src.ui.navigation import PAGE_ORDER, PAGE_SPECS, Page

    assert PAGE_ORDER == (
        Page.OVERVIEW,
        Page.SURVIVAL_ANALYSIS,
        Page.MODEL_COMPARISON,
        Page.GENE_INSIGHTS,
        Page.DATA_COHORT,
        Page.METHODOLOGY_ABOUT,
        Page.ABOUT,
    )
    assert [PAGE_SPECS[page].label for page in PAGE_ORDER] == [
        "Overview",
        "Patient Analysis",
        "Model Evaluation",
        "Gene Insights",
        "Dataset",
        "Methodology",
        "About",
    ]


def test_app_css_retains_accessible_responsive_visual_infrastructure() -> None:
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
    ):
        assert token in APP_CSS
    assert "@media (max-width: 768px)" in APP_CSS
    assert "flex-direction: column" in APP_CSS
    assert ":focus-visible" in APP_CSS
    assert ".cv-surface" in APP_CSS


def test_apply_theme_injects_only_the_trusted_static_stylesheet(monkeypatch) -> None:
    from src.ui import theme

    recorder = _ThemeRecorder()
    monkeypatch.setattr(theme, "st", recorder)

    theme.apply_theme()

    assert recorder.calls == [("markdown", f"<style>{theme.APP_CSS}</style>", True)]


def test_navigation_uses_accessible_group_labels_and_stable_widget_keys(monkeypatch) -> None:
    from src.ui import navigation
    from src.ui.navigation import Page

    recorder = _NavigationRecorder()
    monkeypatch.setattr(navigation, "st", recorder)

    selected = navigation.render_navigation()

    assert selected is Page.OVERVIEW
    assert recorder.calls == [
        {
            "label": "ONCOMAP",
            "options": (Page.OVERVIEW,),
            "labels": ("Overview",),
            "key": "oncomap_navigation_oncomap",
            "index": 0,
        },
        {
            "label": "ANALYSIS",
            "options": (Page.SURVIVAL_ANALYSIS, Page.MODEL_COMPARISON, Page.GENE_INSIGHTS),
            "labels": ("Patient Analysis", "Model Evaluation", "Gene Insights"),
            "key": "oncomap_navigation_analysis",
            "index": None,
        },
        {
            "label": "RESEARCH",
            "options": (Page.DATA_COHORT, Page.METHODOLOGY_ABOUT, Page.ABOUT),
            "labels": ("Dataset", "Methodology", "About"),
            "key": "oncomap_navigation_research",
            "index": None,
        },
    ]


def test_layout_helpers_render_research_status_and_escape_pending_copy(monkeypatch) -> None:
    from src.ui.components import layout

    recorder = _StreamlitRecorder()
    monkeypatch.setattr(layout, "st", recorder)

    layout.render_page_header("Overview", "Research workspace")
    layout.render_shell_status()
    layout.render_empty_state(
        '<script>alert("title")</script>',
        "Unsafe & <strong>message</strong>",
        'Read <a href="/next">the guide</a>',
    )

    assert recorder.calls == [
        ("title", "Overview"),
        ("caption", "Research workspace"),
        (
            "markdown",
            '<div class="cv-status-pill" role="status">'
            '<span aria-hidden="true">●</span> Research prototype</div>',
            True,
        ),
        (
            "markdown",
            '<section class="cv-surface" role="status">'
            '<h2>&lt;script&gt;alert(&quot;title&quot;)&lt;/script&gt;</h2>'
            '<p>Unsafe &amp; &lt;strong&gt;message&lt;/strong&gt;</p>'
            '<p><strong>Next:</strong> Read &lt;a href=&quot;/next&quot;&gt;the guide&lt;/a&gt;</p>'
            "</section>",
            True,
        ),
    ]
