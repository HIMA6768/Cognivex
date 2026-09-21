"""Bridge page for Breast Cancer Subtype & SHAP Intelligence Dashboard."""

from __future__ import annotations


from src.container.cloud_featured_analyzer import render_feature


def render() -> None:
    """Render the cloud-integrated subtype classifier and SHAP analyzer."""
 
    render_feature()