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
            margin-left: 300px !important;
            background: var(--hc-bg);
        }}

        .hc-sidebar {{
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            z-index: 3000 !important;
            box-sizing: border-box;
            width: 300px !important;
            height: 100vh !important;
            overflow-y: auto !important;
            background: #F8FAFC;
            border-right: 1px solid var(--hc-border);
        }}

        .hc-sidebar-nav {{
            display: flex;
            flex-direction: column;
        }}

        @media (max-width: 1023px) {{
            .hc-sidebar {{
                width: 100% !important;
                height: auto !important;
                max-height: none !important;
                padding: 12px 16px !important;
                border-right: none;
                border-bottom: 1px solid var(--hc-border);
                overflow: visible !important;
            }}

            .hc-sidebar-brand,
            .hc-sidebar-helper,
            .hc-sidebar-spacer,
            .hc-sidebar-divider,
            .hc-sidebar-footer {{
                display: none !important;
            }}

            .hc-sidebar-nav {{
                flex-direction: row;
                flex-wrap: nowrap;
                overflow-x: auto;
                width: 100%;
                padding-bottom: 2px;
            }}

            .hc-sidebar-nav-item {{
                flex: 1 1 0 !important;
                width: 0 !important;
                min-width: 0 !important;
                margin-bottom: 0 !important;
                padding: 8px 6px !important;
                font-size: 12px !important;
            }}

            .hc-sidebar-nav-item .q-btn__content {{
                white-space: normal !important;
                text-align: center;
                line-height: 1.2;
            }}

            .hc-sidebar .q-btn.hc-nav-item,
            .hc-sidebar .q-btn.hc-nav-active {{
                color: var(--hc-accent) !important;
            }}

            .hc-shell {{
                margin-left: 0 !important;
                margin-top: 72px !important;
            }}
        }}

        .hc-card {{
            background: var(--hc-card);
            border: 1px solid var(--hc-border);
            border-radius: 8px;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.07);
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

        .hc-sidebar .q-btn.hc-nav-item,
        .hc-sidebar .q-btn.hc-nav-active {{
            background: var(--hc-card) !important;
            color: var(--hc-accent) !important;
            border-radius: 12px !important;
            text-transform: none !important;
            box-shadow: none !important;
        }}

        .hc-sidebar .q-btn.hc-nav-item {{
            border: 1px solid var(--hc-border) !important;
            font-weight: 500 !important;
        }}

        .hc-sidebar .q-btn.hc-nav-active {{
            border: 1px solid var(--hc-accent) !important;
            font-weight: 600 !important;
        }}

        .hc-sidebar .q-btn.hc-nav-item .q-icon,
        .hc-sidebar .q-btn.hc-nav-active .q-icon {{
            color: var(--hc-accent) !important;
        }}

        .hc-sidebar-menu-button {{
            color: var(--hc-accent) !important;
            background: rgba(255, 255, 255, 0.55) !important;
            border: 1px solid var(--hc-border) !important;
        }}

        .hc-sidebar-menu {{
            background: var(--hc-card) !important;
            border: 1px solid var(--hc-border) !important;
            border-radius: 8px !important;
            box-shadow: 0 18px 45px rgba(23, 50, 77, 0.12) !important;
        }}

        .hc-setting-card {{
            background: #FFFFFF;
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
