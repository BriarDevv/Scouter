import { describe, it, expect } from 'vitest'
import { formatRelativeTime } from '@/lib/formatters'

describe('formatRelativeTime', () => {
  it('returns "Ahora" for future dates', () => {
    const future = new Date(Date.now() + 60_000).toISOString()
    expect(formatRelativeTime(future)).toBe('Ahora')
  })

  it('returns "Ahora" for dates less than 1 minute ago', () => {
    const recent = new Date(Date.now() - 30_000).toISOString()
    expect(formatRelativeTime(recent)).toBe('Ahora')
  })

  it('returns "Hace Xm" for recent past minutes', () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60_000).toISOString()
    expect(formatRelativeTime(fiveMinutesAgo)).toBe('Hace 5m')
  })

  it('returns "Hace Xh" for hours ago', () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60_000).toISOString()
    expect(formatRelativeTime(twoHoursAgo)).toBe('Hace 2h')
  })

  it('returns "Hace Xd" for days ago (less than 7)', () => {
    const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60_000).toISOString()
    expect(formatRelativeTime(threeDaysAgo)).toBe('Hace 3d')
  })
})
