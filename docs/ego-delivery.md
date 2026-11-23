# Ego Lite delivery and reply monitoring

The collection adapter can also serve greeting delivery and HR reply monitoring.
Set an existing, Agent-controlled task space ID in the local YAML configuration:

```yaml
collection:
  ego_task_space_id: 7
delivery:
  ego_task_space_id: 7
```

`delivery.ego_task_space_id` applies to `send_greetings`, reply scans, monitor
cycles, detected-reply processing, monitor-tab cleanup and the workbench's
open-chat action. Collection keeps its separate configuration. Omit the delivery
setting or use `null` to keep the original Browser Runtime. A positive integer is
required; invalid, missing or user-controlled configured spaces stop execution
without falling back to CDP or creating a browser, profile or task space.

Create/select the task space using the running Ego Lite and `ego-browser`, sign
in there if necessary, and retain Agent control while BossHunter uses it. The
numeric ID is local session state; update it if the space is closed. BossHunter
only attaches to it. Delivery and monitor share this ID. Browser scope is carried
through cancellable monitor page waits and reset after each workflow, so it does
not reroute independent collection or other threads. Existing browser workflow
locking still applies.

The existing daily quota, send windows, delays, pre-greeting browsing, risk
checks and workbench confirmation are unchanged. The monitor's auto-reply and
follow-up switches still apply; this option does not enable outbound automation.

For a no-send smoke check, run the sender against a temporary database and stop
at `_click_chat_button` before calling its original implementation. At that
breakpoint, evaluate the sender's button-location script with `btn.click()`
removed. Inspect the input only in an existing conversation opened from the chat
list. Never click “立即沟通”, preset greeting confirmation or send controls during
this check: starting a new conversation can itself trigger platform behavior.
A no-send check verifies navigation and selectors, not successful delivery.
