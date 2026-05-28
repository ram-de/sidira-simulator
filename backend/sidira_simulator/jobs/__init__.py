"""JobRunner abstraction — direct invocation for MVP, swappable to queue in Phase 2."""

from sidira_simulator.jobs.runner import InProcessJobRunner, JobRunner

__all__ = ["JobRunner", "InProcessJobRunner"]
