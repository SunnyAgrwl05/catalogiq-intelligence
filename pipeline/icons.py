"""
Inline SVG icon set for CatalogIQ's UI.

All icons are hand-authored, single-color, stroke-based line icons (24x24
viewBox, currentColor stroke) so they inherit whatever color is set via
CSS and never depend on an external image file or network fetch. This
keeps the demo fully offline-safe -- no broken image icons if the judge's
wifi drops mid-demo.
"""

from __future__ import annotations

_STROKE = 'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"'


def _svg(inner: str, size: int = 22) -> str:
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" {_STROKE}>{inner}</svg>'


ICONS: dict[str, str] = {
    # KPI card icons
    "products": _svg('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/><path d="M8 4v5"/>'),
    "trust": _svg('<path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z"/><path d="M9 12l2 2 4-4"/>'),
    "auto": _svg('<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.5 2.5L16 9.5"/>'),
    "review": _svg('<circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/>'),
    "conflict": _svg('<path d="M12 3l9 16H3L12 3z"/><path d="M12 10v4"/><circle cx="12" cy="17" r="0.6" fill="currentColor" stroke="none"/>'),

    # evidence type icons
    "mpn_pattern": _svg('<rect x="3" y="7" width="18" height="10" rx="1.5"/><path d="M7 11v3M11 11v3M15 11v3M19 11v3"/>', 18),
    "description": _svg('<path d="M5 3h10l4 4v14H5z"/><path d="M15 3v4h4"/><path d="M8 12h8M8 15h8M8 9h4"/>', 18),
    "reference_data": _svg('<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6"/><path d="M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>', 18),
    "input_field": _svg('<rect x="3" y="8" width="18" height="8" rx="2"/><path d="M7 12h.01M11 12h6"/>', 18),
    "correction_memory": _svg('<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 5v5h5"/><path d="M12 8v4l3 2"/>', 18),
    "category_rule": _svg('<path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"/>', 18),

    # decision icons
    "AUTO_APPROVED": _svg('<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.5 2.5L16 9.5"/>', 16),
    "REVIEW_REQUIRED": _svg('<circle cx="12" cy="12" r="9"/><path d="M12 8v5"/><circle cx="12" cy="16" r="0.6" fill="currentColor" stroke="none"/>', 16),
    "INVESTIGATE": _svg('<path d="M12 3l9 16H3L12 3z"/><path d="M12 10v4"/><circle cx="12" cy="17" r="0.6" fill="currentColor" stroke="none"/>', 16),

    # misc
    "pipeline_arrow": _svg('<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>', 16),
    "upload": _svg('<path d="M12 3v12"/><path d="M7 8l5-5 5 5"/><path d="M4 17v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/>', 18),
}


def icon(name: str, color: str | None = None) -> str:
    """Return an inline SVG icon string. If color is given, wraps it in a
    span that sets CSS color (SVG uses stroke=currentColor)."""
    svg = ICONS.get(name, "")
    if color:
        return f'<span style="color:{color}; display:inline-flex; vertical-align:middle;">{svg}</span>'
    return svg


LOGO_MARK = """
<svg width="34" height="34" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
  <circle cx="20" cy="20" r="18" fill="none" stroke="#60A5FA" stroke-width="1.6" opacity="0.55"/>
  <circle cx="20" cy="9" r="3.4" fill="#60A5FA"/>
  <circle cx="10" cy="27" r="3.4" fill="#38BDF8"/>
  <circle cx="30" cy="27" r="3.4" fill="#818CF8"/>
  <path d="M20 12.4L11.6 24.2M20 12.4l8.4 11.8M13.4 27h13.2" stroke="#93C5FD" stroke-width="1.6" stroke-linecap="round"/>
</svg>
"""
