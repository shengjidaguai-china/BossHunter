import { FileText, RefreshCw, Star, Trash2, Upload, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

export type ResumeLibraryItem = {
  id: string
  name: string
  focus: string
  label: string
  path: string
  primary: boolean
  exists: boolean
  size: number
  updated_at: string | null
}

type LibraryPayload = {
  resumes?: ResumeLibraryItem[]
  primary_id?: string
  max_resumes?: number
  error?: string
}

type ResumeLibrarySectionProps = {
  currentResumePath?: string
  onPrimaryChange?: (path: string) => void
}

function formatSize(size: number): string {
  if (!size) return '—'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

/**
 * Multiple resumes: every job is scored against all of them and the best match
 * becomes the job's resume (greeting + tailored resume follow that choice).
 */
export function ResumeLibrarySection({ currentResumePath = '', onPrimaryChange }: ResumeLibrarySectionProps) {
  const [items, setItems] = useState<ResumeLibraryItem[]>([])
  const [maxResumes, setMaxResumes] = useState(8)
  const [focus, setFocus] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const fileInput = useRef<HTMLInputElement | null>(null)

  const applyPayload = useCallback((payload: LibraryPayload) => {
    if (payload.error) {
      setError(payload.error)
      return
    }
    const resumes = payload.resumes || []
    setItems(resumes)
    if (payload.max_resumes) setMaxResumes(payload.max_resumes)
    const primary = resumes.find((item) => item.primary)
    if (primary && onPrimaryChange && primary.path !== currentResumePath) {
      onPrimaryChange(primary.path)
    }
  }, [currentResumePath, onPrimaryChange])

  const load = useCallback(async () => {
    try {
      const res = await fetch('/api/resumes')
      const data = (await res.json().catch(() => ({}))) as LibraryPayload
      if (!res.ok) {
        setError(data.error || '读取简历库失败')
        return
      }
      applyPayload(data)
      setError('')
    } catch {
      setError('网络错误，无法读取简历库')
    }
  }, [applyPayload])

  useEffect(() => {
    void load()
  }, [load])

  const uploadFiles = async (files: FileList | null) => {
    if (!files || !files.length) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      for (const file of Array.from(files)) {
        const form = new FormData()
        form.append('file', file)
        if (focus.trim()) form.append('focus', focus.trim())
        const res = await fetch('/api/resumes/upload', { method: 'POST', body: form })
        const data = (await res.json().catch(() => ({}))) as LibraryPayload
        if (!res.ok || data.error) {
          setError(data.error || `上传 ${file.name} 失败`)
          break
        }
        applyPayload(data)
        setNotice(`已加入简历库：${file.name}`)
      }
      setFocus('')
    } catch {
      setError('网络错误，简历上传失败')
    } finally {
      setBusy(false)
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  const setPrimary = async (id: string) => {
    setBusy(true)
    try {
      const res = await fetch(`/api/resumes/${encodeURIComponent(id)}/primary`, { method: 'POST' })
      const data = (await res.json().catch(() => ({}))) as LibraryPayload
      if (!res.ok || data.error) setError(data.error || '设置默认简历失败')
      else {
        applyPayload(data)
        setNotice('已设为主简历')
        setError('')
      }
    } finally {
      setBusy(false)
    }
  }

  const remove = async (item: ResumeLibraryItem) => {
    if (!window.confirm(`删除简历「${item.label}」？该文件会一并删除。`)) return
    setBusy(true)
    try {
      const res = await fetch(`/api/resumes/${encodeURIComponent(item.id)}`, { method: 'DELETE' })
      const data = (await res.json().catch(() => ({}))) as LibraryPayload
      if (!res.ok || data.error) setError(data.error || '删除简历失败')
      else {
        applyPayload(data)
        setNotice(`已删除：${item.label}`)
        setError('')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mt-4 rounded-xl border border-card-border bg-surface p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-bold">简历库（多份简历，按岗位择优）</p>
          <p className="mt-0.5 text-xs text-muted">
            评分时会把岗位和每一份简历对比，取最匹配的一份作为该岗位的简历；招呼语和定制简历也跟随它。
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted">{items.length}/{maxResumes}</span>
          <button
            type="button"
            className="rounded-lg border border-card-border px-2 py-1 text-xs hover:bg-card"
            onClick={() => void load()}
            disabled={busy}
          >
            <RefreshCw className="mr-1 inline h-3 w-3" />刷新
          </button>
        </div>
      </div>

      <div className="mb-2 flex flex-wrap items-center gap-2">
        <input
          value={focus}
          onChange={(event) => setFocus(event.target.value)}
          placeholder="方向标签，如：AI 应用开发（可选）"
          className="min-w-[200px] flex-1 rounded-lg border border-card-border bg-card px-2 py-1 text-xs"
        />
        <label className="inline-flex cursor-pointer items-center gap-1 rounded-lg border border-card-border bg-card px-2 py-1 text-xs hover:border-primary/50">
          <Upload className="h-3 w-3" />
          {busy ? '处理中…' : '添加简历'}
          <input
            ref={fileInput}
            type="file"
            accept=".md,.docx,.pdf,application/pdf"
            multiple
            className="hidden"
            onChange={(event) => void uploadFiles(event.target.files)}
          />
        </label>
      </div>

      {items.length ? (
        <ul className="space-y-2">
          {items.map((item) => (
            <li
              key={item.id}
              className={`flex flex-wrap items-center justify-between gap-2 rounded-lg border p-2 ${
                item.primary ? 'border-primary/40 bg-card' : 'border-card-border bg-card/50'
              }`}
            >
              <div className="min-w-0">
                <p className="flex items-center gap-1 text-xs font-bold">
                  <FileText className="h-3 w-3" />
                  <span className="truncate">{item.label}</span>
                  {item.primary ? (
                    <span className="rounded bg-primary/15 px-1 text-[10px] text-primary">主简历</span>
                  ) : null}
                  {!item.exists ? <span className="text-[10px] text-danger">文件缺失</span> : null}
                </p>
                <p className="truncate text-[11px] text-muted">
                  {formatSize(item.size)} · {item.updated_at || '—'}
                </p>
              </div>
              <div className="flex items-center gap-1">
                {!item.primary ? (
                  <button
                    type="button"
                    className="rounded border border-card-border px-2 py-1 text-[11px] hover:bg-surface"
                    onClick={() => void setPrimary(item.id)}
                    disabled={busy}
                  >
                    <Star className="mr-1 inline h-3 w-3" />设为主简历
                  </button>
                ) : null}
                <button
                  type="button"
                  className="rounded border border-card-border px-2 py-1 text-[11px] text-danger hover:bg-surface"
                  onClick={() => void remove(item)}
                  disabled={busy}
                >
                  <Trash2 className="mr-1 inline h-3 w-3" />删除
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-muted">还没有简历。上传第一份后会成为主简历。</p>
      )}

      {notice ? <p className="mt-2 text-xs text-success">{notice}</p> : null}
      {error ? (
        <p className="mt-2 flex items-center gap-1 rounded-lg bg-danger-soft px-2 py-1 text-xs text-danger">
          <X className="h-3 w-3" />
          {error}
        </p>
      ) : null}
    </div>
  )
}
