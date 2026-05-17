"""Central registry of domain sub-agents.

The orchestrator imports REGISTRY to assemble the full tool list and dispatch
tool calls. The /chat/{domain} endpoint looks up the agent by name.
"""
from app.agents.base import DomainAgent
from app.agents.files_agent import FilesAgent
from app.agents.finance_agent import FinanceAgent
from app.agents.ideas_agent import IdeasAgent
from app.agents.ledger_agent import LedgerAgent
from app.agents.schedule_agent import ScheduleAgent
from app.agents.todo_agent import TodoAgent


REGISTRY: dict[str, DomainAgent] = {
    "schedule": ScheduleAgent(),
    "todo": TodoAgent(),
    "ledger": LedgerAgent,
    "finance": FinanceAgent,
    "ideas": IdeasAgent,
    "files": FilesAgent(),
}
