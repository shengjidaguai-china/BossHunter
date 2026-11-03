import { useCallback, useEffect, useState } from 'react'
import type { Job } from '@/hooks/useDashboard'
import { hasInvalidSalaryRange, useDebouncedValue, type JobFilters } from '@/lib/jobFilters'

interface JobSearchResponse {
  items: Job[]
  total: number
  all_total: number
  city_options?: string[]
  limit: number
  offset: number
}

export type JobSortKey = 'salary' | 'education' | 'score' | 'status' | 'hr_active' | 'created_at'
export type JobSortOrder = 'asc' | 'desc'

export function useJobSearch(
  filters: JobFilters,
  page: number,
  pageSize: number,
  sortBy: JobSortKey = 'created_at',
  sortOrder: JobSortOrder = 'desc',
) {
  const debouncedQuery = useDebouncedValue(filters.query, 250)
  const [items, setItems] = useState<Job[]>([])
  const [total, setTotal] = useState(0)
  const [allTotal, setAllTotal] = useState(0)
  const [cityOptions, setCityOptions] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null)
  const [revision, setRevision] = useState(0)
  const refresh = useCallback(() => setRevision(value => value + 1), [])

  useEffect(() => {
    if (hasInvalidSalaryRange(filters)) {
      setItems([])
      setTotal(0)
      setLoading(false)
      setError('')
      return
    }

    const params = new URLSearchParams({
      limit: String(pageSize),
      offset: String(page * pageSize),
    })
    if (debouncedQuery.trim()) params.set('q', debouncedQuery.trim())
    if (filters.minScore) params.set('min_score', filters.minScore)
    if (filters.salaryMin) params.set('salary_min', filters.salaryMin)
    if (filters.salaryMax) params.set('salary_max', filters.salaryMax)
    filters.status.forEach(value => params.append('status', value))
    if (filters.createdWithin) params.set('created_within', filters.createdWithin)
    filters.sourcePlatform.forEach(value => params.append('source_platform', value))
    filters.city.forEach(value => params.append('city', value))
    filters.education.forEach(value => params.append('education', value))
    filters.recruitmentType.forEach(value => params.append('recruitment_type', value))
    params.set('sort_by', sortBy)
    params.set('sort_order', sortOrder)

    let disposed = false
    let activeController: AbortController | null = null
    const load = async (background = false) => {
      if (activeController) return
      const controller = new AbortController()
      activeController = controller
      const timeout = window.setTimeout(() => controller.abort(), 15000)
      if (!background) setLoading(true)
      try {
        const response = await fetch(`/api/jobs/search?${params.toString()}`, { cache: 'no-store', signal: controller.signal })
        const data: JobSearchResponse & { error?: string } = await response.json()
        if (!response.ok) throw new Error(data.error || '岗位筛选失败')
        if (disposed || controller.signal.aborted) return
        setItems(data.items)
        setTotal(data.total)
        setAllTotal(data.all_total)
        setCityOptions(data.city_options || [])
        setLastRefreshedAt(new Date())
        setError('')
      } catch (cause) {
        if (!disposed) setError(controller.signal.aborted ? '岗位刷新超时，将自动重试。' : cause instanceof Error ? cause.message : '岗位筛选失败')
      } finally {
        window.clearTimeout(timeout)
        activeController = null
        if (!disposed) setLoading(false)
      }
    }

    void load()
    // Refresh in place: background updates must keep the table, selection and page visible.
    const timer = window.setInterval(() => void load(true), 5000)
    const refreshOnFocus = () => { void load(true) }
    const refreshWhenVisible = () => {
      if (document.visibilityState === 'visible') void load(true)
    }
    window.addEventListener('focus', refreshOnFocus)
    document.addEventListener('visibilitychange', refreshWhenVisible)
    return () => {
      disposed = true
      window.clearInterval(timer)
      activeController?.abort()
      window.removeEventListener('focus', refreshOnFocus)
      document.removeEventListener('visibilitychange', refreshWhenVisible)
    }
  }, [debouncedQuery, filters.minScore, filters.salaryMin, filters.salaryMax, filters.status, filters.createdWithin, filters.sourcePlatform, filters.city, filters.education, filters.recruitmentType, page, pageSize, sortBy, sortOrder, revision])

  return { items, total, allTotal, cityOptions, loading, error, lastRefreshedAt, refresh }
}
