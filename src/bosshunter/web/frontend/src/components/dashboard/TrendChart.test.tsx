import { cloneElement, type ReactElement } from 'react'
import { cleanup, render } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { TrendChart } from './TrendChart'

// Give the real chart a viewport since jsdom does not measure container sizes.
vi.mock('recharts', async (importOriginal) => ({
  ...await importOriginal<typeof import('recharts')>(),
  ResponsiveContainer: ({ children }: { children: ReactElement<{ width: number; height: number }> }) =>
    cloneElement(children, { width: 900, height: 200 }),
}))

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

it('shows seven consecutive days across New Year even with out-of-window activity', () => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2027-01-02T12:00:00Z'))
  const { container } = render(<TrendChart data={[
    { day: '2026-12-26', action: 'sent', cnt: 5 },
    { day: '2026-12-27', action: 'sent', cnt: 2 },
    { day: '2027-01-02', action: 'replied', cnt: 1 },
    { day: '2027-01-03', action: 'sent', cnt: 3 },
  ]} />)
  const ticks = container.querySelectorAll('.recharts-xAxis .recharts-cartesian-axis-tick-value')
  expect(Array.from(ticks, tick => tick.textContent)).toEqual([
    '12-27', '12-28', '12-29', '12-30', '12-31', '01-01', '01-02',
  ])
})
