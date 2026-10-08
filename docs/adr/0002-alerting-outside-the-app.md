# Alerting lives outside the app

uptime-watch records results and exposes them as metrics on `/metrics`; it never sends notifications itself. Alerting belongs to the monitoring stack (Prometheus and Alertmanager), which already handles routing, grouping and silencing. The same stack also watches uptime-watch itself.

## Considered options

- **Built-in notifications** (email, Slack, Discord from the worker): rejected. It duplicates Alertmanager, and every new channel would become app code to maintain.
