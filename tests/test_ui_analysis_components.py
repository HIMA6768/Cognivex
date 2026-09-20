from __future__ import annotations

from dataclasses import dataclass

from src.contracts.inference import (
    AnalysisTrack, FROZEN_SUBTYPE_CLASS_ORDER, PrognosisResult, ResultLineage,
    SubtypeClassificationResult, TrackOutcome, TrackReadinessState,
)


@dataclass
class _Recorder:
    calls: list[tuple]
    def metric(self, label, value): self.calls.append(("metric", label, value))
    def caption(self, value): self.calls.append(("caption", value))
    def subheader(self, value): self.calls.append(("subheader", value))
    def markdown(self, value): self.calls.append(("markdown", value))
    def dataframe(self, value, **_kwargs): self.calls.append(("dataframe", value))
    def warning(self, value): self.calls.append(("warning", value))
    def error(self, value): self.calls.append(("error", value))


def _lineage(track: AnalysisTrack) -> ResultLineage:
    return ResultLineage(track, "test", "r9-v1", "a" * 64)


def test_parse_contract_lines_preserves_partial_input_and_nullable_values() -> None:
    from src.ui.components.analysis import parse_contract_lines, parse_contract_value

    parsed = parse_contract_lines(
        "gata3=1.25\ngata3_mut=R175H\ntumor_size=null\n",
        allowed_fields=("gata3", "gata3_mut", "tumor_size"),
        numeric_fields=("gata3", "tumor_size"), nullable_fields=("tumor_size",),
    )
    assert parsed == {"gata3": 1.25, "gata3_mut": "R175H", "tumor_size": None}
    assert parse_contract_value("tumor_size", "null", numeric_fields=("tumor_size",), nullable_fields=("tumor_size",)) is None
    assert parse_contract_value("gata3", "1.25", numeric_fields=("gata3",), nullable_fields=()) == 1.25


def test_render_ready_track_outputs_only_frozen_r9_result_shapes(monkeypatch) -> None:
    from src.ui.components import analysis

    recorder = _Recorder([])
    monkeypatch.setattr(analysis, "st", recorder)
    prognosis = PrognosisResult(_lineage(AnalysisTrack.TRACK_A), "log_partial_hazard", "Model log relative hazard score", 0.25, "Model-relative log partial hazard; not an absolute survival probability, mortality probability, risk category, treatment recommendation, or clinical prognosis.")
    subtype = SubtypeClassificationResult(_lineage(AnalysisTrack.TRACK_C), "LumA", FROZEN_SUBTYPE_CLASS_ORDER, (0.1, 0.1, 0.4, 0.2, 0.1, 0.1))

    analysis.render_track_outcome(TrackOutcome(AnalysisTrack.TRACK_A, TrackReadinessState.READY, prognosis, None))
    analysis.render_track_outcome(TrackOutcome(AnalysisTrack.TRACK_C, TrackReadinessState.READY, subtype, None))

    assert ("metric", "Model log relative hazard score", "0.2500") in recorder.calls
    assert any(call[0] == "dataframe" and list(call[1]["Subtype"]) == list(FROZEN_SUBTYPE_CLASS_ORDER) for call in recorder.calls)


def test_render_missing_state_is_safe_and_actionable(monkeypatch) -> None:
    from src.ui.components import analysis
    from src.contracts.inference import TrackError

    recorder = _Recorder([])
    monkeypatch.setattr(analysis, "st", recorder)
    outcome = TrackOutcome(AnalysisTrack.TRACK_B, TrackReadinessState.MISSING_REQUIRED_FIELDS, None, TrackError("MISSING_REQUIRED_FIELDS", "Required input fields are missing", AnalysisTrack.TRACK_B, missing_fields=("gata3",)))

    analysis.render_track_outcome(outcome)
    assert recorder.calls == [("warning", "Track B: Required input fields are missing Missing fields: gata3.")]


def test_submit_track_request_passes_partial_values_to_r9_unchanged() -> None:
    from src.ui.components.analysis import submit_track_request

    class Service:
        def analyze(self, request):
            self.request = request
            return "response"

    service = Service()
    assert submit_track_request(service, AnalysisTrack.TRACK_A, {"age_at_diagnosis": 50.0}) == "response"
    assert service.request.requested_tracks == (AnalysisTrack.TRACK_A,)
    assert service.request.features == {"age_at_diagnosis": 50.0}
