# GeoAgent

GeoAgent is a distributed system that simulates a fleet of software agents running on customer endpoints. Each agent connects to a central backend to receive work, execute geospatial data processing, report results, and stay operational — even when the network, the broker, or the agent process itself fails along the way.

The project is designed as a realistic testbed for the engineering problems that come with running software you don't fully control: endpoints that reboot, connections that drop, messages that get delivered twice, and processes that crash mid-job.

## What GeoAgent Is For

The goal is not to build a GIS platform or to recreate Google Earth Engine. The geospatial dataset — Dynamic World / Sentinel-2, partitioned by region and time window — exists to give the system a large, realistic, partitionable workload. The actual subject of the project is the distributed systems engineering around that workload:

- Coordinating many independent agents from a central backend
- Moving work reliably over a message queue
- Surviving crashes, restarts, and network partitions without losing or duplicating work
- Making failure visible, diagnosable, and recoverable

## Conceptual Architecture

```
                        ┌─────────────────────────┐
                        │      Central Backend      │
                        │  REST API · Job Manager   │
                        │ Agent Manager · Log Manager│
                        └────────────┬───────────────┘
                                     │
                            ┌────────┴────────┐
                            │  Message Queue   │
                            └────────┬────────┘
                                     │
              ┌──────────────┬──────┴───────┬──────────────┐
              │              │              │              │
         ┌────▼────┐   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
         │ GeoAgent │   │ GeoAgent │   │ GeoAgent │   │ GeoAgent │
         │ (endpoint)│   │ (endpoint)│   │ (endpoint)│   │ (endpoint)│
         └──────────┘   └──────────┘   └──────────┘   └──────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │   Result Store (Spark)   │
                        │  Large-scale aggregation  │
                        └─────────────────────────┘
```

The backend owns the source of truth for agents and jobs and exposes it over a REST API. Work is distributed through a message queue rather than direct backend-to-agent calls, so agents can come and go, retry independently, and be replaced without the backend needing to track live connections. Results produced by the fleet ultimately land in a store that Apache Spark reads for large-scale aggregation.

## What an Agent Will Be Able To Do

Once complete, every GeoAgent instance will:

1. Register itself with the backend and obtain an identity
2. Maintain a periodic heartbeat so the backend knows it is alive and how busy it is
3. Receive jobs from the message queue
4. Execute jobs concurrently, without letting execution block the heartbeat or registration
5. Query and process partitions of a geospatial dataset
6. Report progress and final results back to the backend
7. Keep its own local state, independent of the backend's availability
8. Recover cleanly from interruptions, crashes, or restarts — resuming or safely discarding whatever was in flight
9. Retry failed operations using a policy that distinguishes transient failures from permanent ones
10. Guarantee that a duplicated message or a redelivered job never results in duplicated work or duplicated results
11. Emit structured, correlated logs that let a single job be traced across the whole system
12. Do all of the above concurrently, as a supervised set of background tasks rather than a single blocking loop

## What the Backend Will Be Able To Do

The backend is the coordination layer for the fleet:

- **Agent Manager** — tracks which agents exist, their capabilities, and whether they are online, stale, or offline
- **Job Manager** — owns the lifecycle of a job from creation through a well-defined state machine to a terminal state
- **Log Manager** — ingests structured logs shipped from agents and makes them queryable for troubleshooting
- **REST API** — the single, versioned, authenticated interface through which agents and operators interact with the system

## Dataset and Workload

Jobs represent a unit of geospatial work defined by a region, a time range, a dataset, and an operation to perform — for example, computing a land-cover distribution or an NDVI summary over a partition of Dynamic World / Sentinel-2 data. A large area and time span is split into many such partitions so that the fleet of agents can process them in parallel, and so that partitioning, retries, and recovery all have a meaningful unit of work to operate on.

## Engineering Concerns the Project Is Built Around

- **Concurrency** — agents run heartbeat, job consumption, execution, and result reporting as independent, supervised concurrent tasks
- **Networking** — every network call has explicit timeouts and a clear distinction between transient and permanent failure
- **Message queues** — at-least-once delivery, visibility timeouts, redelivery, and a dead letter queue for messages that repeatedly fail
- **Persistence** — each agent keeps enough local state to survive a restart without losing track of what it was doing
- **Self-healing and recovery** — agents and the backend both reconcile their state automatically after an interruption, without manual intervention
- **Retry policies** — backoff, jitter, and limits applied consistently across REST calls, queue operations, and job execution
- **Idempotency** — the system is designed so that duplicate delivery or duplicate retries never produce duplicate effects
- **Structured logging and observability** — every log line is correlated by job, agent, and request, and the backend exposes metrics on the health of the fleet
- **Triage and troubleshooting** — dedicated tooling for tracing a job's full history, grouping failures by cause, and acting on the dead letter queue
- **Testing** — a unit test suite that runs without real infrastructure, and an integration suite that exercises the system against real failure scenarios
- **Fault injection** — controlled, deliberate failure scenarios (dead agents, broker outages, corrupted state) used to validate that the resilience mechanisms actually hold
- **Large-scale processing** — an Apache Spark pipeline that aggregates the results produced by the fleet into region- and time-level summaries

## Development Approach

GeoAgent is being built incrementally, feature by feature, starting from the project's base architecture and data models and working up toward a full end-to-end workflow: submitting a large geospatial job, having it distributed across multiple agents, surviving injected failures along the way, and finishing with a Spark aggregation over the results. Architecturally significant features are specified before they are implemented, and every feature that touches meaningful behavior is expected to ship with tests.

## Status

This project is under active development. The codebase does not yet exist; this document describes the system GeoAgent is intended to become.
