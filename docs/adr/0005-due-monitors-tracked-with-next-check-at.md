# Due monitors are tracked with a stored next check time

Each monitor stores when its next check is due (`next_check_at`). Every few seconds the scheduler selects the monitors that are due, queues a job for each and moves their next check time one interval ahead in the same transaction. A job that waits on the queue longer than one interval expires unrun, because a newer job for the same monitor is already behind it.

The scheduler holds a Postgres advisory lock while it runs. A second copy cannot take the lock, so it waits and logs that another scheduler is active, and it takes over if the first one dies.

## Considered options

- **Derive due-ness from the latest Result** (`last checked_at + interval <= now`): no extra column, but a check that is queued and not yet finished still looks due, so it would be queued again on every tick. The query also grows with the results table.
- **RQ's built-in scheduling** (`enqueue_in`, cron scheduler): would replace our scheduler process and contradict [ADR 0001](0001-scheduler-queue-worker-split.md), which keeps the decision of *when* in one place we own.
- **Rely on the deployment alone** for the single scheduler (Compose, Kubernetes `replicas: 1`): a rolling update starts the new copy before it stops the old one, so two schedulers overlap for a moment. The lock rules that out; the deployment setting still keeps the normal case tidy.

## Consequences

- Creating or resuming a monitor sets its next check time to now; changing the interval sets it to now plus the new interval.
- After a long worker outage, monitors are checked once each when workers return, not once per missed interval.
