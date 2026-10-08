import { describe, expect, it } from 'vitest'
import { EMPTY_JOB_FILTERS, filterJobs, hasActiveJobFilters, type JobFilters } from './jobFilters'
import type { Job } from '@/hooks/useDashboard'

function job(overrides: Partial<Job>): Job {
  return {
    id: 'job', source_platform: 'boss', title: '岗位', company: '公司', salary: '10K', city: '北京', experience: '',
    education: '本科', recruitment_type: 'experienced', jd: '', score: 80, score_reason: '', greeting: '', status: 'ready',
    hr_name: '', hr_title: '', hr_active: '', company_size: '', company_industry: '', url: '', created_at: '', ...overrides,
  }
}

describe('job multi-select filters', () => {
  it('matches any selected value within a field', () => {
    const filters: JobFilters = { ...EMPTY_JOB_FILTERS, sourcePlatform: ['boss', 'zhilian'], status: ['ready', 'filtered'] }
    expect(filterJobs([
      job({ id: 'boss-ready' }),
      job({ id: 'zhilian-filtered', source_platform: 'zhilian', status: 'filtered' }),
      job({ id: 'liepin-ready', source_platform: 'liepin' }),
    ], filters).map(item => item.id)).toEqual(['boss-ready', 'zhilian-filtered'])
  })

  it('treats unknown education as an option alongside recognized values', () => {
    const filters: JobFilters = { ...EMPTY_JOB_FILTERS, education: ['硕士', 'unknown'] }
    expect(filterJobs([job({ id: 'master', education: '硕士' }), job({ id: 'unknown', education: '' }), job({ id: 'bachelor' })], filters).map(item => item.id)).toEqual(['master', 'unknown'])
  })

  it('matches any selected city, including district-suffixed labels', () => {
    const filters: JobFilters = { ...EMPTY_JOB_FILTERS, city: ['北京', '上海'] }
    expect(filterJobs([
      job({ id: 'beijing' }),
      job({ id: 'shanghai-pudong', city: '上海·浦东新区' }),
      job({ id: 'shenzhen', city: '深圳' }),
    ], filters).map(item => item.id)).toEqual(['beijing', 'shanghai-pudong'])
  })

  it('does not count empty multi-selects as active filters', () => {
    expect(hasActiveJobFilters(EMPTY_JOB_FILTERS)).toBe(false)
    expect(hasActiveJobFilters({ ...EMPTY_JOB_FILTERS, status: ['ready'] })).toBe(true)
  })
})
