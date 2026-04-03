from __future__ import annotations


def format_signals(signals: list) -> str:
    if not signals:
        return "None detected"
    return ", ".join(f"{s.signal_type.value}: {s.detail or 'N/A'}" for s in signals)


def get_client_module():
    from app.llm import client as client_module

    return client_module
