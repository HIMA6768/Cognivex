"""Operational upload limits independent of AI and quality-gate settings."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UploadSettings:
    """Safe file-upload limits for the Streamlit prototype."""

    max_upload_mb: int = 10

    @property
    def max_upload_bytes(self) -> int:
        """Return the configured upload limit in bytes."""
        return self.max_upload_mb * 1024 * 1024
