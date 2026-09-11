/** Optional browser-only integration. Never pass a whole Job/API response across this boundary. */
export interface InterviewJob {
  company: string
  target_role: string
  city: string
  salary: string
  education: string
  jd: string
}

export type HandoffState = 'waiting' | 'received' | 'blocked' | 'timeout'
type JobSource = { title?: unknown; company?: unknown; city?: unknown; salary?: unknown; education?: unknown; jd?: unknown }

function localRoot(raw: string): URL {
  if (!/^http:\/\/(127\.0\.0\.1|localhost):[1-9]\d{0,4}\/?$/.test(raw)) {
    throw new Error('只支持 http://127.0.0.1:端口 或 http://localhost:端口，不可包含路径、参数或凭据。')
  }
  const url = new URL(raw)
  if (!url.port) throw new Error('请使用服务实际输出的非 80 端口。')
  return url
}

export function interviewTarget(raw: string, sourceOrigin: string): URL {
  const target = localRoot(raw.trim())
  const source = localRoot(sourceOrigin)
  if (target.origin === source.origin) throw new Error('面试工作台地址不能是 BossHunter 自己的地址。')
  target.searchParams.set('import', 'job')
  target.searchParams.set('source', source.origin)
  return target
}

function text(value: unknown): string {
  if (value == null) return ''
  if (typeof value !== 'string') throw new Error('岗位字段格式异常，请重新读取详情。')
  return value.trim()
}

function fields(job: JobSource): InterviewJob {
  return { company: text(job.company), target_role: text(job.title), city: text(job.city), salary: text(job.salary), education: text(job.education), jd: text(job.jd) }
}

export function jobForInterview(job: JobSource): InterviewJob {
  const result = fields(job)
  if (!result.target_role || !result.jd) throw new Error('需要岗位名称和完整 JD 才能交接，请先补全岗位详情。')
  const limits: Record<keyof InterviewJob, number> = { company: 160, target_role: 160, city: 80, salary: 100, education: 80, jd: 15000 }
  if (Object.entries(limits).some(([key, limit]) => result[key as keyof InterviewJob].length > limit)) {
    throw new Error('岗位内容超过直接交接的长度上限（JD 15,000 字）；请下载 JD 后手动导入，原文不会被截断。')
  }
  return result
}

export function jobMarkdown(job: JobSource): string {
  const value = fields(job)
  return `# 面试岗位材料\n\n公司：${value.company}\n岗位：${value.target_role}\n城市：${value.city}\n薪资原文：${value.salary}\n学历：${value.education}\n\n## JD 原文\n\n${value.jd}\n`
}

/** The caller must run this inside a user click and show the data/target before sending. */
export function startInterviewHandoff(host: Window, address: string, job: InterviewJob, onState: (state: HandoffState) => void): () => void {
  const target = interviewTarget(address, host.location.origin)
  let popup: Window | null = null
  let sent = false
  let finished = false
  let timer: number | undefined
  const cleanup = () => {
    finished = true
    host.removeEventListener('message', receive)
    if (timer !== undefined) host.clearTimeout(timer)
  }
  const finish = (state: HandoffState) => { cleanup(); onState(state) }
  const receive = (event: MessageEvent) => {
    if (finished || event.origin !== target.origin || event.source !== popup || !popup) return
    if (!event.data || event.data.version !== 1) return
    if (event.data.type === 'interview-sim:ready' && !sent) {
      sent = true
      popup.postMessage({ type: 'interview-sim:job', version: 1, job }, target.origin)
    } else if (event.data.type === 'interview-sim:received' && sent) {
      finish('received')
    }
  }
  host.addEventListener('message', receive)
  // A fresh tab and opener are required for the authenticated window/origin handshake.
  // Only use an explicitly trusted local service; the receiver drops opener after receiving.
  try { popup = host.open(target.href, '_blank') } catch (error) { cleanup(); throw error }
  if (!popup) { finish('blocked'); return cleanup }
  onState('waiting')
  timer = host.setTimeout(() => finish('timeout'), 15000)
  return cleanup
}
