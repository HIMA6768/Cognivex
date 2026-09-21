from __future__ import annotations

import logging
from pathlib import Path

import pytest


def test_ui_service_accessor_caches_one_repository_relative_r9_construction(monkeypatch) -> None:
    from src.ui import analysis_service

    calls: list[Path] = []
    sentinel = object()

    def construct(root: Path) -> object:
        calls.append(root)
        return sentinel

    analysis_service.get_analysis_service.clear()
    try:
        monkeypatch.setattr(analysis_service.AnalysisService, "from_canonical_artifacts", construct)

        assert analysis_service.get_analysis_service() is sentinel
        assert analysis_service.get_analysis_service() is sentinel
        assert calls == [Path(__file__).resolve().parents[1]]
    finally:
        analysis_service.get_analysis_service.clear()


def test_ui_service_accessor_logs_initialization_failure_without_exposing_it_to_callers(monkeypatch, caplog) -> None:
    """A deployed artifact-load failure must be diagnosable in server logs only."""
    from src.ui import analysis_service

    def fail(_root: Path) -> object:
        raise RuntimeError("simulated frozen artifact load failure")

    analysis_service.get_analysis_service.clear()
    try:
        monkeypatch.setattr(analysis_service.AnalysisService, "from_canonical_artifacts", fail)

        with caplog.at_level(logging.ERROR, logger="src.services.analysis"):
            with pytest.raises(RuntimeError, match="simulated frozen artifact load failure"):
                analysis_service.get_analysis_service()

        assert "[ONCOMAP_INIT_ERROR]" in caplog.text
        assert "RuntimeError" in caplog.text
        assert "simulated frozen artifact load failure" in caplog.text
        assert "repository_root=" in caplog.text
        assert "python_version=" in caplog.text
        assert "package_versions=" in caplog.text
        assert "canonical_artifact_files=" in caplog.text
        assert "preprocessor.pkl" in caplog.text
        assert "pipeline.pkl" in caplog.text
        assert "Traceback" in caplog.text
        assert any(record.name == "src.services.analysis" for record in caplog.records)
    finally:
        analysis_service.get_analysis_service.clear()
