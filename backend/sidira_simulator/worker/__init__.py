"""Out-of-process workers (#268 Phase 2).

Currently houses the persona-pack build worker, which polls Postgres for PENDING
``persona_build_runs`` and runs them off the API's request path. See
:mod:`sidira_simulator.worker.persona_worker`.
"""
