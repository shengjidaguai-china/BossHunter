# Opt-in applications and platform feedback

New delivery adapters support Liepin, Zhilian and 51job through the existing Ego task-space backend. They default to disabled and do not use a CDP fallback. A positive integer `delivery.ego_task_space_id` and the platform's literal `enabled: true` are required. Per-platform `daily_limit` defaults to 10; BOSS retains its existing throttle settings.

```yaml
delivery:
  ego_task_space_id: 7
  cross_platform_dedup: false
  platforms:
    liepin: {enabled: false, daily_limit: 10}
    zhilian: {enabled: false, daily_limit: 10}
    51job: {enabled: false, daily_limit: 10}
```

`GET /api/workbench` exposes `delivery_capabilities`, `monitor_capabilities` and platform quotas. A confirmed client supplies full `expected_actions` and `expected_platforms` maps keyed by selected job ID to `POST /api/workbench/deliver`. They are checked at admission and again before execution, including batches appended to existing tasks. The first external automatic application requires exactly one explicit selected job with both maps. The client must show platform, action, company and job before obtaining the user's confirmation.

Delivery reserves quota and checks prior applications transactionally. `delivery.cross_platform_dedup` defaults to `false` (including when omitted): the same company and role can be applied to again on another platform because its recruiter may differ. Set it to `true` to restore cross-platform company deduplication: historical applications, outstanding reservations and site-observed existing applications then block another platform's application to the same company, including BOSS history. Company matching normalizes full-width characters, case, whitespace, common punctuation and legal suffixes; it does not infer brand aliases. Under either setting, the same platform job ID cannot be sent again, including when only an uncertain reservation remains. The first-application pilot gate and quotas also remain in force. Authoritative job eligibility is checked before reservation and again immediately before the page action. Unknown outcomes retain the reservation and must be reconciled manually; they are not automatically retried.

The three apply controls have been located without clicking: Liepin `a[data-selector="apply-job"]` / 投简历; Zhilian `button.a-button` / 立即投递; 51job `div.apply-btn-new.big` / 立即投递 with the detail URL's job ID. The adapter requires matching job identity and a unique visible control. Captcha, abnormal account or throttling stops the operation and writes `需要扫码.txt`. No genuine application receipt has been accepted yet.

## Monitoring acceptance

- Zhilian: reads the official progress page and recognizes only the observed `企业对你有意` feedback with matching source job ID, company, title and a complete timestamp. Status `replied` and idempotent `hr_reply_detected` history are written atomically. This is platform feedback, not a claim that HR-authored chat text was read.
- 51job: its actual account showed an empty official application list. Read-only empty-list inspection is implemented, but nonempty feedback parsing remains unverified and cannot generate reply events. `platform_supports(..., "monitor", ...)` returns false.
- Liepin: authentication was unavailable. Reply monitoring and chat greetings remain unsupported. A confirmed resume application never silently falls back to a greeting.

BOSS chat and follow-up processing exclude external jobs. The job-agent watch integration consumes explicit reply history across the four platforms; it does not itself scrape these sites or start monitor tasks.

The real first application and successful receipt remain user acceptance steps. Development verification must stop before apply/message buttons. Offline tests use synthetic DOM, disposable databases and mocked Ego; the original proxy-starting integration tests must be excluded when the session forbids new debug listeners.
