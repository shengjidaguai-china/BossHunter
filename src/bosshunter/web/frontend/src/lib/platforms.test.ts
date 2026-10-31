import { expect, it } from 'vitest'
import { withPlatformSafetyDefaults, platformSafetyError } from './platforms'
it('materializes defaults without mutating the source or enabling platforms', () => {
  const original = { platforms: { liepin: { enabled: false } } }
  const result = withPlatformSafetyDefaults(original)
  for (const id of ['zhilian', '51job', 'liepin']) expect(result.platforms[id].safety).toEqual({ daily_search_page_limit: 20, daily_detail_page_limit: 50, daily_platform_page_limit: 80, daily_delivery_limit: 10 })
  expect(result.platforms.liepin.enabled).toBe(false)
  expect(result.platforms.zhilian.enabled).toBeUndefined()
  expect(original).toEqual({ platforms: { liepin: { enabled: false } } })
  expect(platformSafetyError(result)).toBeNull()
})
