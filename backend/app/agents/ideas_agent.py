"""Stub for ideas (아이디어·노트) domain."""
from typing import Any

from app.agents.base import StubAgent


IDEAS_TOOLS: list[dict[str, Any]] = [
    {
        "name": "ideas.create_note",
        "description": "Create a new note with title, body, and tags.",
        "input_schema": {
            "type": "object",
            "required": ["title", "body"],
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    {
        "name": "ideas.search_semantic",
        "description": "Semantic search across notes.",
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "ideas.extract_action_items",
        "description": "Extract candidate todo items from a note.",
        "input_schema": {
            "type": "object",
            "required": ["note_id"],
            "properties": {"note_id": {"type": "string"}},
        },
    },
]


IdeasAgent = StubAgent("ideas", IDEAS_TOOLS)
