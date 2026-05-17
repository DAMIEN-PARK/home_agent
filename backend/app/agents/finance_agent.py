"""Stub for finance (재무·자산) domain."""
from typing import Any

from app.agents.base import StubAgent


FINANCE_TOOLS: list[dict[str, Any]] = [
    {
        "name": "finance.update_valuation",
        "description": "Refresh the valuation of an account or holding as of a given date.",
        "input_schema": {
            "type": "object",
            "required": ["account"],
            "properties": {
                "account": {"type": "string"},
                "as_of": {"type": "string", "description": "ISO date"},
            },
        },
    },
    {
        "name": "finance.net_worth_snapshot",
        "description": "Return current net-worth snapshot across accounts.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "finance.list_accounts",
        "description": "List the user's accounts (cash / savings / brokerage / debt).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "finance.list_holdings",
        "description": "List investment holdings with current valuation.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


FinanceAgent = StubAgent("finance", FINANCE_TOOLS)
