# automation-worker

- Purpose: Background execution engine for automations and asynchronous jobs.
- Will contain: Rule evaluation runners, retry logic, scheduled jobs, notification dispatch, and OTA job processing.
- Responsibilities: Execute background work without turning Home OS into a synchronous bottleneck.
- Interfaces: Consumes canonical state and events from Home OS modules; publishes results back through internal APIs and audit events.
- Status: planned.
