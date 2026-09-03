"""CSS and visual tokens for the Health Companion interface."""

from __future__ import annotations

from nicegui import ui

from config import PALETTE


def apply_global_styles() -> None:
    """Register global CSS for a premium editorial healthcare interface."""
    ui.add_head_html(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        """,
        shared=True,
    )
    ui.add_css(
        f"""
        :root {{
            --hc-bg: {PALETTE.background};
            --hc-card: {PALETTE.card};
            --hc-text: {PALETTE.text};
            --hc-muted: {PALETTE.secondary_text};
            --hc-accent: {PALETTE.accent};
            --hc-border: {PALETTE.border};
        }}

        body {{
            background: var(--hc-bg);
            color: var(--hc-text);
            font-family: Inter, Arial, sans-serif;
        }}

        .q-page {{
            background: var(--hc-bg);
        }}

        .hc-shell {{
            min-height: 100vh;
            background: var(--hc-bg);
        }}

        .hc-sidebar {{
            background: #efe8dc;
            border-right: 1px solid var(--hc-border);
        }}

        .hc-card {{
            background: var(--hc-card);
            border: 1px solid var(--hc-border);
            border-radius: 8px;
            box-shadow: 0 18px 45px rgba(23, 50, 77, 0.07);
        }}

        .hc-card-flat {{
            background: var(--hc-card);
            border: 1px solid var(--hc-border);
            border-radius: 8px;
        }}

        .hc-serif {{
            font-family: "Instrument Serif", Georgia, serif;
            letter-spacing: 0;
        }}

        .hc-muted {{
            color: var(--hc-muted);
        }}

        .hc-accent {{
            color: var(--hc-accent);
        }}

        .hc-button {{
            background: var(--hc-accent) !important;
            color: #fff !important;
            border-radius: 8px !important;
            text-transform: none !important;
            font-weight: 600 !important;
            box-shadow: none !important;
        }}

        .hc-button-secondary {{
            background: transparent !important;
            color: var(--hc-accent) !important;
            border: 1px solid var(--hc-border) !important;
            border-radius: 8px !important;
            text-transform: none !important;
            font-weight: 600 !important;
            box-shadow: none !important;
        }}

        .hc-nav-item {{
            background: rgba(255, 255, 255, 0.35) !important;
            color: var(--hc-text) !important;
            border: 1px solid rgba(23, 50, 77, 0.08) !important;
            border-radius: 12px !important;
            text-transform: none !important;
            font-weight: 500 !important;
        }}

        .hc-nav-active {{
            background: var(--hc-accent) !important;
            color: #fff !important;
            border: 1px solid transparent !important;
            border-radius: 12px !important;
            text-transform: none !important;
            font-weight: 600 !important;
        }}

        .hc-panel-toggle {{
            position: fixed !important;
            top: 96px !important;
            left: 264px !important;
            z-index: 3000 !important;
            width: 36px !important;
            height: 36px !important;
            color: #fff !important;
            background: var(--hc-accent) !important;
            border: 1px solid var(--hc-accent) !important;
            border-radius: 8px !important;
            box-shadow: 0 12px 28px rgba(23, 50, 77, 0.18) !important;
            transition: left 180ms ease, transform 180ms ease, background 180ms ease !important;
        }}

        .hc-panel-toggle-open {{
            left: 264px !important;
        }}

        .hc-panel-toggle-closed {{
            left: 18px !important;
        }}

        .hc-panel-toggle:hover {{
            transform: translateX(2px);
            background: #244a70 !important;
        }}

        .hc-sidebar-menu-button {{
            color: var(--hc-accent) !important;
            background: rgba(255, 255, 255, 0.55) !important;
            border: 1px solid rgba(23, 50, 77, 0.08) !important;
        }}

        .hc-sidebar-menu {{
            background: var(--hc-card) !important;
            border: 1px solid var(--hc-border) !important;
            border-radius: 8px !important;
            box-shadow: 0 18px 45px rgba(23, 50, 77, 0.12) !important;
        }}

        .hc-setting-card {{
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(255, 252, 247, 0.96));
        }}

        .hc-status-chip {{
            border-radius: 999px;
            padding: 0.3rem 0.75rem;
            font-size: 12px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
        }}

        .hc-status-success {{
            color: #1b6b43;
            background: rgba(46, 94, 78, 0.1);
        }}

        .hc-status-warning {{
            color: #8a5a10;
            background: rgba(138, 90, 16, 0.12);
        }}

        .hc-status-danger {{
            color: #8b2f2f;
            background: rgba(139, 47, 47, 0.1);
        }}

        .hc-fade-in {{
            animation: hcFadeIn 240ms ease-out both;
        }}

        @keyframes hcFadeIn {{
            from {{
                opacity: 0;
                transform: translateY(8px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        .q-field--outlined .q-field__control {{
            border-radius: 8px;
            background: #fffdfa;
        }}

        .q-field__label, .q-field__native, .q-field__prefix, .q-field__suffix {{
            color: var(--hc-text);
            font-family: Inter, Arial, sans-serif;
        }}

        .hc-report p, .hc-report li {{
            line-height: 1.7;
            color: var(--hc-text);
            font-size: 15px;
        }}

        .body--dark {{
            --hc-bg: #151412;
            --hc-card: #201f1b;
            --hc-text: #F7F3EA;
            --hc-muted: #b9b2a7;
            --hc-accent: #c9d9ee;
            --hc-border: #3a3832;
            background: var(--hc-bg);
        }}

        .body--dark .hc-sidebar {{
            background: #1a1916;
        }}

        .body--dark .q-field--outlined .q-field__control {{
            background: #24231f;
        }}
        """,
        shared=True,
    )
