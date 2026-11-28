export const PLATFORM_IDS = ['boss', 'zhilian', '51job', 'liepin', 'shixiseng'] as const
export type PlatformId = typeof PLATFORM_IDS[number]

export function isPlatformId(value: unknown): value is PlatformId {
  return PLATFORM_IDS.some(platform => platform === value)
}

export function isShixisengJobUrl(url: string) {
  return /^https:\/\/www\.shixiseng\.com\/intern\/inn_[A-Za-z0-9]+$/.test(url)
}

export const PLATFORM_LABELS: Record<string, string> = {
  boss: 'BOSS 直聘',
  zhilian: '智联招聘',
  '51job': '前程无忧',
  liepin: '猎聘',
  shixiseng: '实习僧',
}

export const PLATFORM_SHORT_LABELS: Record<string, string> = {
  boss: 'BOSS',
  zhilian: '智联',
  '51job': '51job',
  liepin: '猎聘',
  shixiseng: '实习僧',
}
