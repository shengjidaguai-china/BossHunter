import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import type { Job } from '@/hooks/useDashboard'
import { jobForInterview, jobMarkdown, startInterviewHandoff, type HandoffState } from '@/lib/interviewHandoff'

const ADDRESS_KEY = 'bosshunter.interview-workbench-url'
const messages: Record<HandoffState, string> = {
  waiting: '正在等待本地面试工作台接收（最多 15 秒）…',
  received: '岗位草稿已送达；请到新标签页补充简历、核对并保存，再选择面试配置。尚未开始面试。',
  blocked: '浏览器拦截了新标签页。请允许弹窗后重试，或下载 JD 手动导入。',
  timeout: '未收到接收确认：请确认面试服务已启动且支持岗位交接。若新页已有草稿，请先核对，避免重复操作；也可以下载 JD 手动导入。',
}

export function InterviewPreparation({ job }: { job: Job }) {
  const [expanded, setExpanded] = useState(false)
  const [address, setAddress] = useState(() => {
    try { return localStorage.getItem(ADDRESS_KEY) || 'http://127.0.0.1:8800' } catch { return 'http://127.0.0.1:8800' }
  })
  const [confirmed, setConfirmed] = useState(false)
  const [state, setState] = useState<HandoffState | null>(null)
  const [notice, setNotice] = useState('')
  const cancel = useRef<(() => void) | null>(null)
  const waiting = state === 'waiting'
  let preview = '', dataError = ''
  try { preview = jobMarkdown(job) } catch { dataError = '岗位字段格式异常，请重新读取详情。' }
  useEffect(() => () => cancel.current?.(), [])

  const send = () => {
    if (!confirmed || waiting) return
    cancel.current?.()
    setNotice('')
    try {
      const payload = jobForInterview(job)
      cancel.current = startInterviewHandoff(window, address, payload, next => {
        setState(next)
        setNotice(messages[next])
      })
      try { localStorage.setItem(ADDRESS_KEY, address.trim()) } catch { /* Address persistence is optional. */ }
    } catch (error) {
      setState(null)
      setNotice(error instanceof Error ? error.message : '交接失败，请下载 JD 手动导入。')
    }
  }

  const download = () => {
    try {
      const blob = new Blob([jobMarkdown(job)], { type: 'text/markdown;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'interview-job.md'
      link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      setNotice('JD 已下载。可交给其他 Agent，或在面试实验室的岗位导入中选择此文件。')
    } catch (error) {
      setNotice(error instanceof Error ? error.message : '下载失败。')
    }
  }

  return (
    <section className="mt-4 border-t border-card-border pt-4" aria-label="面试准备">
      <Button type="button" variant="secondary" size="sm" aria-expanded={expanded} onClick={() => setExpanded(value => !value)}>准备面试</Button>
      {expanded && (
        <div className="mt-3 space-y-3 text-sm">
          <p className="text-muted">将这个岗位用于模拟面试，不会投递或修改岗位状态。不安装面试工具也能下载 JD，交给其他 Agent 使用。</p>
          <p className="text-muted">仅交接公司、岗位、城市、薪资、学历和 JD 原文；不包含你的简历、密钥、HR 字段、招呼语和聊天记录。JD 原文本身可能含联系方式，请先核对下方内容。</p>
          <details className="rounded-lg border border-card-border p-3">
            <summary className="cursor-pointer font-bold">查看将交接的岗位内容</summary>
            <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-words font-sans text-xs leading-5">{dataError || preview}</pre>
          </details>
          <label className="block font-bold">本地面试工作台地址
            <input className="mt-1 block w-full rounded-md border border-card-border bg-white px-3 py-2 font-normal focus-visible:outline-primary" value={address} disabled={waiting} onChange={event => { setAddress(event.target.value); setConfirmed(false) }} spellCheck={false} />
          </label>
          <p className="text-xs text-muted">先让 Agent 启动 Interview Sim，再填写它实际输出的地址。只支持同一台电脑上的 localhost / 127.0.0.1。首次安装和协议版本见 <a className="text-primary underline" href="https://github.com/miaomiao636/interview-sim#readme" target="_blank" rel="noopener noreferrer">面试实验室文档</a>。</p>
          <label className="flex items-start gap-2"><input type="checkbox" className="mt-1 accent-primary" checked={confirmed} disabled={waiting} onChange={event => setConfirmed(event.target.checked)} /><span>我已核对岗位内容，信任此本地服务，同意交接以上招聘资料。</span></label>
          <div className="flex flex-wrap gap-2">
            <Button type="button" size="sm" disabled={!confirmed || waiting || !!dataError} onClick={send}>{waiting ? '等待接收…' : '打开并交接岗位'}</Button>
            <Button type="button" variant="secondary" size="sm" disabled={!!dataError} onClick={download}>下载 JD（Markdown）</Button>
            {waiting && <Button type="button" variant="ghost" size="sm" onClick={() => { cancel.current?.(); setState(null); setNotice('已停止等待；已打开的标签页保留，请自行核对。') }}>停止等待</Button>}
          </div>
        </div>
      )}
      {notice && <p className="mt-3 text-sm text-primary" role="status" aria-live="polite">{notice}</p>}
    </section>
  )
}
