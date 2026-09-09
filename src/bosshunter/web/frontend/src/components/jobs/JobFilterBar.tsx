import { useState } from 'react'
import { ChevronDown, ChevronUp, RotateCcw, Search, SlidersHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { STATUS_LABELS } from '@/lib/status'
import { hasActiveJobFilters, type JobFilters } from '@/lib/jobFilters'

interface JobFilterBarProps {
  filters: JobFilters
  onChange: (filters: JobFilters) => void
  onReset: () => void
  resultCount: number
  totalCount: number
  invalidSalary?: boolean
  showStatus?: boolean
  showSource?: boolean
}

export function JobFilterBar({
  filters,
  onChange,
  onReset,
  resultCount,
  totalCount,
  invalidSalary = false,
  showStatus = false,
  showSource = false,
}: JobFilterBarProps) {
  const [mobileExpanded, setMobileExpanded] = useState(false)
  const update = (key: keyof JobFilters, value: string) => onChange({ ...filters, [key]: value })

  const hasAdvancedFilters = Boolean(
    filters.minScore ||
    filters.salaryMin ||
    filters.salaryMax ||
    filters.status ||
    filters.sourcePlatform ||
    filters.education ||
    filters.recruitmentType
  )

  const showAdvancedOnMobile = mobileExpanded || hasAdvancedFilters
  const advancedClass = showAdvancedOnMobile ? 'min-w-0' : 'min-w-0 hidden md:block'

  return (
    <div className="mb-4 rounded-2xl border border-card-border bg-[#FFFCFA] p-3">
      <div className="grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2 2xl:grid-cols-4">
        <label className="relative min-w-0 md:col-span-2 2xl:col-span-1">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted" />
          <Input
            value={filters.query}
            onChange={event => update('query', event.target.value)}
            placeholder="搜索职位、公司、JD 或评分理由"
            className="pl-9"
            aria-label="关键词"
          />
        </label>
        <Select className="min-w-0" value={filters.createdWithin} onChange={event => update('createdWithin', event.target.value)} aria-label="采集时间">
          <option value="">采集时间：全部</option>
          <option value="today">今天</option>
          <option value="3d">近 3 天</option>
          <option value="7d">近 7 天</option>
        </Select>
        <Select className={advancedClass} value={filters.minScore} onChange={event => update('minScore', event.target.value)} aria-label="最低评分">
          <option value="">最低评分：不限</option>
          <option value="60">60+</option>
          <option value="71">71+</option>
          <option value="80">80+</option>
        </Select>
        <Input
          type="number"
          min="0"
          step="1"
          value={filters.salaryMin}
          onChange={event => update('salaryMin', event.target.value)}
          placeholder="最低薪资 K"
          className={advancedClass}
          aria-label="最低薪资 K"
        />
        <Input
          type="number"
          min="0"
          step="1"
          value={filters.salaryMax}
          onChange={event => update('salaryMax', event.target.value)}
          placeholder="最高薪资 K"
          className={advancedClass}
          aria-label="最高薪资 K"
        />
        {showStatus && (
          <Select className={advancedClass} value={filters.status} onChange={event => update('status', event.target.value)} aria-label="岗位状态">
            <option value="">全部状态</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </Select>
        )}
        {showSource && (
          <Select className={advancedClass} value={filters.sourcePlatform} onChange={event => update('sourcePlatform', event.target.value)} aria-label="来源平台">
            <option value="">来源平台：全部</option>
            <option value="boss">BOSS 直聘</option>
            <option value="zhilian">智联招聘</option>
            <option value="51job">前程无忧</option>
          </Select>
        )}
        <Select className={advancedClass} value={filters.education} onChange={event => update('education', event.target.value)} aria-label="学历要求">
          <option value="">学历：全部</option>
          <option value="博士">博士</option>
          <option value="硕士">硕士</option>
          <option value="本科">本科</option>
          <option value="大专">大专</option>
          <option value="不限">学历不限</option>
          <option value="unknown">未识别</option>
        </Select>
        <Select className={advancedClass} value={filters.recruitmentType} onChange={event => update('recruitmentType', event.target.value)} aria-label="招聘类型">
          <option value="">招聘类型：全部</option>
          <option value="campus">校招</option>
          <option value="experienced">社招</option>
          <option value="unknown">未识别</option>
        </Select>
        <div className="flex min-h-9 min-w-0 flex-wrap items-center justify-between gap-2 rounded-md border border-card-border bg-white px-3 py-1">
          <span className="whitespace-nowrap text-xs font-bold text-muted">结果 {resultCount} / 总数 {totalCount}</span>
          <div className="flex items-center gap-1">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 px-2 md:hidden"
              onClick={() => setMobileExpanded(!mobileExpanded)}
            >
              <SlidersHorizontal className="mr-1 h-3 w-3 text-primary" />
              {showAdvancedOnMobile ? '收起' : '更多'}
              {showAdvancedOnMobile ? <ChevronUp className="ml-1 h-3 w-3" /> : <ChevronDown className="ml-1 h-3 w-3" />}
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 px-2"
              disabled={!hasActiveJobFilters(filters)}
              onClick={onReset}
            >
              <RotateCcw className="mr-1 h-3 w-3" />重置
            </Button>
          </div>
        </div>
      </div>
      {invalidSalary && <p className="mt-2 text-xs font-bold text-danger">最低薪资不能高于最高薪资，请调整后再筛选。</p>}
    </div>
  )
}
