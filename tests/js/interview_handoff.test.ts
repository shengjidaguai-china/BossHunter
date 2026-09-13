import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  interviewTarget, jobForInterview, jobMarkdown, startInterviewHandoff,
} from '../../src/bosshunter/web/frontend/src/lib/interviewHandoff.ts'

const job = { company: '合成公司', title: '测试工程师', city: '测试城', salary: '10-15K', education: '本科', jd: '完整岗位职责', resume_path: 'private', greeting: 'private', hr_name: 'private', api_key: 'private' }

test('only explicit loopback roots are accepted; no data is put into URL', () => {
  assert.equal(interviewTarget('http://127.0.0.1:8800/', 'http://localhost:8686').href,
    'http://127.0.0.1:8800/?import=job&source=http%3A%2F%2Flocalhost%3A8686')
  for (const value of ['https://example.com', 'http://127.1:8800', 'http://2130706433:8800', 'http://localhost.evil:8800', 'http://localhost:8800/path', 'http://user@localhost:8800', 'http://localhost:8800?x=1', 'http://localhost:8800/#x', 'http://localhost:65536', 'http://localhost:80', 'http://localhost:0']) {
    assert.throws(() => interviewTarget(value, 'http://localhost:8686'), undefined, value)
  }
  assert.throws(() => interviewTarget('http://localhost:8686', 'http://localhost:8686'))
  assert.throws(() => interviewTarget('http://localhost:8800', 'https://external.example'))
})

test('explicit allowlist excludes applicant, recruiter and model data', () => {
  const result = jobForInterview(job)
  assert.deepEqual(result, { company: job.company, target_role: job.title, city: job.city, salary: job.salary, education: job.education, jd: job.jd })
  assert(!JSON.stringify(result).includes('private'))
  assert.throws(() => jobForInterview({ ...job, jd: ' ' }))
  assert.throws(() => jobForInterview({ ...job, jd: 'x'.repeat(15001) }))
  assert.throws(() => jobForInterview({ ...job, company: 123 }))
  assert.equal(jobForInterview({ title: '测试', jd: '职责', city: null }).city, '')
})

test('Markdown fallback preserves long JD and exports no private fields', () => {
  const text = jobMarkdown({ ...job, jd: 'x'.repeat(20000) })
  assert(text.includes('x'.repeat(20000)))
  assert(text.includes('测试工程师'))
  assert(!text.includes('private'))
})

function harness(blocked = false) {
  const listeners = new Set<(event: MessageEvent) => void>()
  const messages: unknown[][] = []
  const states: string[] = []
  const timers = new Set<() => void>()
  const popup = { postMessage: (...args: unknown[]) => messages.push(args) }
  const host = {
    location: { origin: 'http://localhost:8686' },
    open: () => blocked ? null : popup,
    addEventListener: (_: string, listener: (event: MessageEvent) => void) => listeners.add(listener),
    removeEventListener: (_: string, listener: (event: MessageEvent) => void) => listeners.delete(listener),
    setTimeout: (callback: () => void) => { timers.add(callback); return callback },
    clearTimeout: (callback: () => void) => timers.delete(callback),
  }
  const cancel = startInterviewHandoff(host as unknown as Window, 'http://127.0.0.1:8800', jobForInterview(job), state => states.push(state))
  const emit = (type: string, origin = 'http://127.0.0.1:8800', source: unknown = popup, version = 1) => {
    for (const listener of listeners) listener({ data: { type, version }, source, origin } as MessageEvent)
  }
  return { listeners, messages, states, timers, popup, emit, cancel }
}

test('binds handshake to exact origin + window + version; sends once and cleans up', () => {
  const h = harness()
  h.emit('interview-sim:ready', 'http://localhost:8800')
  h.emit('interview-sim:ready', undefined, {})
  h.emit('interview-sim:ready', undefined, undefined, 2)
  h.emit('interview-sim:received')
  assert.equal(h.messages.length, 0)
  h.emit('interview-sim:ready')
  h.emit('interview-sim:ready')
  assert.equal(h.messages.length, 1)
  assert.deepEqual(h.messages[0], [{ type: 'interview-sim:job', version: 1, job: jobForInterview(job) }, 'http://127.0.0.1:8800'])
  h.emit('interview-sim:received')
  assert.equal(h.states.at(-1), 'received')
  assert.equal(h.listeners.size, 0)
  assert.equal(h.timers.size, 0)
})

test('blocked popup, timeout and cancellation do not send a job', () => {
  const blocked = harness(true)
  assert.equal(blocked.states.at(-1), 'blocked')
  assert.equal(blocked.listeners.size, 0)
  const timeout = harness()
  for (const callback of timeout.timers) callback()
  assert.equal(timeout.states.at(-1), 'timeout')
  assert.equal(timeout.listeners.size, 0)
  assert.equal(timeout.messages.length, 0)
  const canceled = harness()
  canceled.cancel()
  canceled.emit('interview-sim:ready')
  assert.equal(canceled.messages.length, 0)
  assert.equal(canceled.timers.size, 0)
})
