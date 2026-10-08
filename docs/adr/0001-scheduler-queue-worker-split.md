# Separate scheduler, queue and workers for running checks

Every monitor must be checked again and again at its interval. One **scheduler** decides which monitors are due and puts a job for each on a Redis queue; **workers** take jobs from the queue and run the checks. This separates deciding *when* from doing the work, so the number of workers can grow with the number of monitors while the schedule stays in one place.

## Considered options

- **A single process that loops over all monitors**: simpler, but its checks run one after another in one place. One slow URL delays every check behind it, and the only way to scale is a bigger machine.

## Consequences

- The scheduler must run as **exactly one copy**. Two schedulers would each queue every due monitor, so every check would run twice. Any deployment (Compose, Kubernetes) has to enforce this, while workers can run as any number of replicas.
- Redis becomes a required dependency, and its queue length is a useful signal: a growing queue means the workers can't keep up.
