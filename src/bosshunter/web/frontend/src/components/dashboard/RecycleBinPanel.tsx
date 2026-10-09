import { RotateCcw, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { Job } from '@/hooks/useDashboard'

interface RecycleBinPanelProps {
  jobs: Job[]
  selectedIds: string[]
  loading: boolean
  onToggleSelected: (id: string) => void
  onSelectAll: (ids: string[]) => void
  onRestore: (ids: string[]) => void
  onPermanentDelete: (ids: string[]) => void
}

export function RecycleBinPanel({
  jobs,
  selectedIds,
  loading,
  onToggleSelected,
  onSelectAll,
  onRestore,
  onPermanentDelete,
}: RecycleBinPanelProps) {
  const allSelected = jobs.length > 0 && jobs.every(job => selectedIds.includes(job.id))
  return (
    <div className="rounded-3xl border border-card-border bg-card p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2"><Trash2 className="h-5 w-5 text-primary" /><h2 className="text-2xl font-black">回收站</h2></div>
          <p className="mt-1 text-sm text-muted">保留岗位状态、评分、招呼语和历史；恢复后也不会自动启动评分或投递。</p>
        </div>
        <span className="rounded-full bg-secondary px-3 py-2 text-xs font-black text-primary">{jobs.length} 条</span>
      </div>
      {loading ? <div className="rounded-2xl border border-card-border bg-surface p-6 text-center text-sm text-muted">正在读取回收站...</div> : (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-2 text-xs">
            <Button variant="secondary" size="sm" disabled={!jobs.length} onClick={() => onSelectAll(allSelected ? [] : jobs.map(job => job.id))}>{allSelected ? '取消全选' : '全选回收站'}</Button>
            <span className="rounded-full bg-secondary px-3 py-2 font-bold text-primary">已选择 {selectedIds.length} 条</span>
            <Button variant="secondary" size="sm" disabled={!selectedIds.length} onClick={() => onRestore(selectedIds)}><RotateCcw className="mr-1 h-3 w-3" />批量恢复</Button>
            <Button variant="destructive" size="sm" disabled={!selectedIds.length} onClick={() => onPermanentDelete(selectedIds)}><Trash2 className="mr-1 h-3 w-3" />永久删除</Button>
          </div>
          <div className="overflow-x-auto rounded-2xl border border-card-border">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-card-border bg-secondary text-xs text-muted"><th className="w-10 px-3 py-3">选</th><th className="px-4 py-3 text-left">公司</th><th className="px-4 py-3 text-left">职位</th><th className="px-4 py-3 text-left">原状态</th><th className="px-4 py-3 text-left">删除时间</th><th className="px-4 py-3 text-right">操作</th></tr></thead>
              <tbody>
                {jobs.map(job => <tr key={job.id} className="border-b border-card-border bg-card"><td className="px-3 py-3 text-center"><input type="checkbox" checked={selectedIds.includes(job.id)} onChange={() => onToggleSelected(job.id)} className="h-4 w-4 accent-primary" /></td><td className="px-4 py-3 font-black">{job.company}</td><td className="px-4 py-3">{job.title}</td><td className="px-4 py-3 text-muted">{job.status}</td><td className="px-4 py-3 text-xs text-muted">{job.deleted_at || '-'}</td><td className="px-4 py-3 text-right"><Button variant="secondary" size="sm" onClick={() => onRestore([job.id])}>恢复</Button><Button className="ml-2" variant="destructive" size="sm" onClick={() => onPermanentDelete([job.id])}>永久删除</Button></td></tr>)}
                {!jobs.length && <tr><td colSpan={6} className="px-4 py-10 text-center text-sm text-muted">回收站为空</td></tr>}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
