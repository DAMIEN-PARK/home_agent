"""Stub for ledger (가계부) domain. Tool schema only; handle_tool returns 501."""
from typing import Any

from app.agents.base import StubAgent


LEDGER_TOOLS: list[dict[str, Any]] = [
    {
        "name": "ledger.add_transaction",
        "description": "Record an expense/income transaction.",
        "input_schema": {
            "type": "object",
            "required": ["amount", "category"],
            "properties": {
                "amount": {"type": "number"},
                "category": {"type": "string"},
                "description": {"type": "string"},
                "occurred_at": {"type": "string"},
                "payment_method": {"type": "string"},
            },
        },
    },
    {
        "name": "ledger.sum_by_category",
        "description": "Sum transactions by category over a period.",
        "input_schema": {
            "type": "object",
            "required": ["month"],
            "properties": {
                "month": {"type": "string", "description": "YYYY-MM"},
                "category": {"type": "string"},
            },
        },
    },
    {
        "name": "ledger.list_transactions",
        "description": "List recent transactions, optionally filtered by category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "ledger.category_inference",
        "description": "Infer the most likely category from a free-text description.",
        "input_schema": {
            "type": "object",
            "required": ["description"],
            "properties": {"description": {"type": "string"}},
        },
    },
]


LedgerAgent = StubAgent("ledger", LEDGER_TOOLS)
