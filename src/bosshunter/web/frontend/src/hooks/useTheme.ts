import { useEffect, useState } from 'react'

export type ThemeMode = 'light' | 'dark' | 'system'

/** 与 index.html 中防闪烁脚本使用的 key 保持一致 */
export const THEME_STORAGE_KEY = 'bosshunter-theme'

const MEDIA_QUERY = '(prefers-color-scheme: dark)'

export function isThemeMode(value: unknown): value is ThemeMode {
  return value === 'light' || value === 'dark' || value === 'system'
}

function readStoredMode(): ThemeMode {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY)
    return isThemeMode(stored) ? stored : 'system'
  } catch {
    return 'system'
  }
}

function prefersDark(): boolean {
  return typeof window !== 'undefined' && window.matchMedia(MEDIA_QUERY).matches
}

export function resolveIsDark(mode: ThemeMode): boolean {
  return mode === 'dark' || (mode === 'system' && prefersDark())
}

function applyMode(mode: ThemeMode) {
  document.documentElement.classList.toggle('dark', resolveIsDark(mode))
}

export function useTheme() {
  const [mode, setMode] = useState<ThemeMode>(readStoredMode)

  useEffect(() => {
    applyMode(mode)
    try {
      localStorage.setItem(THEME_STORAGE_KEY, mode)
    } catch {
      // 隐私模式等禁用存储的场景下，主题仍然生效，只是不持久化
    }
  }, [mode])

  useEffect(() => {
    if (mode !== 'system') return
    const media = window.matchMedia(MEDIA_QUERY)
    const onChange = () => applyMode('system')
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [mode])

  return { mode, setMode }
}
