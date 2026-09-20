from __future__ import annotations

from pathlib import Path


def test_ui_service_accessor_caches_one_repository_relative_r9_construction(monkeypatch) -> None:
    from src.ui import analysis_service

    calls: list[Path] = []
    sentinel = object()

    def construct(root: Path) -> object:
        calls.append(root)
        return sentinel

    analysis_service.get_analysis_service.clear()
    monkeypatch.setattr(analysis_service.AnalysisService, "from_canonical_artifacts", construct)

    assert analysis_service.get_analysis_service() is sentinel
    assert analysis_service.get_analysis_service() is sentinel
    assert calls == [Path(__file__).resolve().parents[1]]
