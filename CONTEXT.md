# uptime-watch

Watches a list of URLs and records whether each one is reachable and how fast it answers.

## Language

**Monitor**:
A URL registered for regular checking, together with how often to check it.
_Avoid_: target, site, endpoint

**Paused**:
A monitor that is kept but not checked until it is resumed.
_Avoid_: disabled, inactive, stopped

**Check**:
One attempt to reach a monitor's URL.
_Avoid_: ping, probe, test

**Result**:
The recorded outcome of one check: up or down, the HTTP status code and the response time, or the reason no response arrived. The response time runs until the response headers arrive; the body is not part of it.
_Avoid_: status, log entry

**Up**:
A check that got a 2xx or 3xx response within the timeout. Anything else is **down**.
_Avoid_: online, healthy, alive

**Interval**:
How often a monitor is checked.
_Avoid_: frequency, period

**Due**:
A monitor that is not paused and whose next check time has passed. A new or resumed monitor is due at once.
_Avoid_: pending, scheduled, ready
