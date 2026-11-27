import { useEffect, useState } from 'react'
import type { Job } from '@/hooks/useDashboard'

export type HrActiveTier = 'online' | 'just_now' | 'today' | 'week' | 'month' | 'older' | 'unknown'

export const HR_ACTIVE_OPTIONS: { value: HrActiveTier; label: string }[] = [
  { value: 'online', label: '在线' },
  { value: 'just_now', label: '刚刚活跃' },
  { value: 'today', label: '今日活跃' },
  { value: 'week', label: '本周内活跃' },
  { value: 'month', label: '本月内活跃' },
  { value: 'older', label: '一月以上' },
  { value: 'unknown', label: '活跃度未知' },
]

const CN_DIGITS: Record<string, number> = {
  零: 0, 一: 1, 二: 2, 两: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9,
}

function parseCnOrArabicInt(token: string): number | null {
  const cleaned = token.trim()
  if (!cleaned) return null
  if (/^\d+$/.test(cleaned)) return Number(cleaned)
  if (cleaned === '十') return 10
  if (cleaned.includes('十')) {
    const [tensPart, onesPart] = cleaned.split('十')
    const tens = tensPart === '' ? 1 : CN_DIGITS[tensPart]
    const ones = onesPart === '' ? 0 : CN_DIGITS[onesPart]
    if (tens === undefined || ones === undefined) return null
    return tens * 10 + ones
  }
  if (cleaned.length === 1 && cleaned in CN_DIGITS) return CN_DIGITS[cleaned]
  return null
}

export function classifyHrActive(hrActive?: string | null): HrActiveTier {
  const text = (hrActive || '').trim()
  if (!text) return 'unknown'
  if (text === '在线') return 'online'
  if (text === '刚刚活跃') return 'just_now'
  if (text === '今日活跃') return 'today'
  if (text === '本周活跃') return 'week'
  if (text === '本月活跃') return 'month'
  if (text === '半年前活跃' || text === '年前活跃') return 'older'

  const match = text.match(/^([0-9一二两三四五六七八九十]+)\s*(日|天|周|个?月)内活跃$/)
  if (!match) return 'unknown'
  const amount = parseCnOrArabicInt(match[1])
  const unit = match[2]
  if (amount === null || amount <= 0) return 'unknown'
  if (unit === '日' || unit === '天') {
    if (amount <= 1) return 'today'
    if (amount <= 7) return 'week'
    if (amount <= 31) return 'month'
    return 'older'
  }
  if (unit === '周') {
    if (amount <= 1) return 'week'
    if (amount <= 4) return 'month'
    return 'older'
  }
  return amount <= 1 ? 'month' : 'older'
}

export interface JobFilters {
  query: string
  minScore: string
  salaryMin: string
  salaryMax: string
  status: string[]
  createdWithin: string
  sourcePlatform: string[]
  city: string[]
  education: string[]
  recruitmentType: string[]
  hrActive: string[]
}

export const EMPTY_JOB_FILTERS: JobFilters = {
  query: '',
  minScore: '',
  salaryMin: '',
  salaryMax: '',
  status: [],
  createdWithin: '',
  sourcePlatform: [],
  city: [],
  education: [],
  recruitmentType: [],
  hrActive: [],
}

export function useDebouncedValue<T>(value: T, delay: number) {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedValue(value), delay)
    return () => window.clearTimeout(timeout)
  }, [value, delay])

  return debouncedValue
}

export function hasInvalidSalaryRange(filters: JobFilters) {
  if (filters.salaryMin === '' || filters.salaryMax === '') return false
  return Number(filters.salaryMin) > Number(filters.salaryMax)
}

export function hasActiveJobFilters(filters: JobFilters) {
  return Object.values(filters).some(value => Array.isArray(value) ? value.length > 0 : value !== '')
}

/** Mirrors the backend: platform city labels look like 上海·浦东新区. */
export function jobCityBaseName(city: string) {
  return (city || '').split('·')[0].trim()
}

function parseMonthlySalaryK(salary: string): [number, number] | null {
  const range = salary.match(/(\d+(?:\.\d+)?)\s*[kK]?\s*-\s*(\d+(?:\.\d+)?)\s*[kK]/)
  if (range) {
    const low = Number(range[1])
    const high = Number(range[2])
    return [Math.min(low, high), Math.max(low, high)]
  }
  const single = salary.match(/(\d+(?:\.\d+)?)\s*[kK](?!\w)/)
  if (single) {
    const value = Number(single[1])
    return [value, value]
  }
  return null
}

function parseCreatedAt(createdAt: string) {
  const value = (createdAt || '').trim()
  if (!value) return null
  const normalized = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}/.test(value)
    ? `${value.replace(' ', 'T')}Z`
    : value
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

function matchesCreatedWithin(createdAt: string, createdWithin: string) {
  if (!createdWithin) return true
  const created = parseCreatedAt(createdAt)
  if (!created) return false
  const now = new Date()
  if (createdWithin === 'today') {
    return created.getFullYear() === now.getFullYear()
      && created.getMonth() === now.getMonth()
      && created.getDate() === now.getDate()
  }
  const days = createdWithin === '3d' ? 3 : 7
  return now.getTime() - created.getTime() <= days * 24 * 60 * 60 * 1000
}

export function filterJobs(jobs: Job[], filters: JobFilters) {
  if (hasInvalidSalaryRange(filters)) return []
  const keyword = filters.query.trim().toLocaleLowerCase()
  const minimumScore = filters.minScore === '' ? null : Number(filters.minScore)
  const salaryMin = filters.salaryMin === '' ? null : Number(filters.salaryMin)
  const salaryMax = filters.salaryMax === '' ? null : Number(filters.salaryMax)
  const salaryEnabled = salaryMin !== null || salaryMax !== null

  return jobs.filter(job => {
    if (!matchesCreatedWithin(job.created_at, filters.createdWithin)) return false
    if (keyword) {
      const searchable = [job.title, job.company, job.jd, job.score_reason]
        .join('\n')
        .toLocaleLowerCase()
      if (!searchable.includes(keyword)) return false
    }
    if (minimumScore !== null && Number(job.score || 0) < minimumScore) return false
    if (filters.status.length > 0 && !filters.status.includes(job.status)) return false
    if (filters.sourcePlatform.length > 0 && !filters.sourcePlatform.includes(job.source_platform || 'boss')) return false
    if (filters.city.length > 0 && !filters.city.includes(jobCityBaseName(job.city))) return false
    if (filters.recruitmentType.length > 0 && !filters.recruitmentType.includes(job.recruitment_type || 'unknown')) return false
    if (filters.education.length > 0 && !filters.education.some(value => value === 'unknown' ? !(job.education || '').trim() : (job.education || '').includes(value))) return false
    if (filters.hrActive.length > 0 && !filters.hrActive.includes(classifyHrActive(job.hr_active))) return false
    if (salaryEnabled) {
      const salaryRange = parseMonthlySalaryK(job.salary || '')
      if (!salaryRange) return false
      const [jobMin, jobMax] = salaryRange
      if (salaryMin !== null && jobMax < salaryMin) return false
      if (salaryMax !== null && jobMin > salaryMax) return false
    }
    return true
  })
}
