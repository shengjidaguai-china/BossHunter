import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const time = '(?:[01][0-9]|2[0-3]):[0-5][0-9]'
const windowPattern = new RegExp(`^\\s*(${time})\\s*-\\s*(${time})\\s*$`)

export function sendWindowsError(value: unknown): string | null {
  if (!Array.isArray(value)) return '发送时间窗口必须是时间段列表，请删除无效项后重新添加。'
  const windows: [string, string][] = []
  for (const item of value) {
    const match = typeof item === 'string' ? windowPattern.exec(item) : null
    if (!match) return '请为每个时间段选择有效的开始时间和结束时间。'
    if (match[1] >= match[2]) return '结束时间必须晚于开始时间，不支持跨午夜。'
    windows.push([match[1], match[2]])
  }
  windows.sort(([a], [b]) => a.localeCompare(b))
  if (windows.some((item, index) => index > 0 && item[0] < windows[index - 1][1])) {
    return '时间段不能重复或重叠；相邻时间段可以共用边界。'
  }
  return null
}

export function SendWindowsInput({ value, onChange }: { value: unknown; onChange: (value: string[]) => void }) {
  const rows = Array.isArray(value) ? value : [value]
  const error = sendWindowsError(value)
  const update = (index: number, side: number, next: string) => {
    onChange(rows.map((item, row) => {
      if (row !== index) return item
      const parts = typeof item === 'string' ? item.split('-').map(part => part.trim()) : ['', '']
      parts[side] = next
      return `${parts[0] || ''}-${parts[1] || ''}`
    }))
  }
  return <div className="space-y-2">
    {rows.map((item, index) => {
      const match = typeof item === 'string' ? windowPattern.exec(item) : null
      const parts = typeof item === 'string' ? item.split('-').map(part => part.trim()) : ['', '']
      return <div key={index} className="flex flex-wrap items-end gap-2 rounded-md border border-card-border p-3">
        <label className="flex-1 min-w-32 text-xs text-muted">开始时间
          <Input type="time" step={60} aria-label={`时间段 ${index + 1} 开始时间`} value={match?.[1] ?? parts[0] ?? ''} onChange={event => update(index, 0, event.target.value)} />
        </label>
        <label className="flex-1 min-w-32 text-xs text-muted">结束时间
          <Input type="time" step={60} aria-label={`时间段 ${index + 1} 结束时间`} value={match?.[2] ?? parts[1] ?? ''} onChange={event => update(index, 1, event.target.value)} />
        </label>
        <Button type="button" variant="ghost" size="sm" aria-label={`删除时间段 ${index + 1}`} onClick={() => onChange(rows.filter((_, row) => row !== index))}>
          {rows.length === 1 ? '删除（取消时间限制）' : '删除'}
        </Button>
      </div>
    })}
    <Button type="button" variant="secondary" size="sm" onClick={() => onChange([...rows, '-'])}>添加时间段</Button>
    {error && <p role="alert" className="text-xs text-danger">{error}</p>}
    {!rows.length && <p role="alert" className="text-xs text-danger">未设置时间窗口：兼容旧配置，将不限制发送时间，也没有每日窗口截止时间。建议添加时间段。</p>}
    <p className="text-xs text-muted">按本机时间执行，包含开始时间、不包含结束时间。窗口之间暂停发送，后台任务在当天最后一个窗口结束时停止。</p>
  </div>
}
