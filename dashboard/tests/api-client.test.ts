import { describe, it, expect } from 'vitest'
import { API_BASE_URL } from '@/lib/constants'

describe('API_BASE_URL', () => {
  it('is defined', () => {
    expect(API_BASE_URL).toBeDefined()
  })

  it('returns "/api/proxy" in browser (jsdom) context where window is defined', () => {
    // In jsdom environment window is defined, so the browser branch is taken
    expect(typeof window).toBe('object')
    expect(API_BASE_URL).toBe('/api/proxy')
  })
})
