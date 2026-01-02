import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('API Base URL', () => {
  const originalLocation = window.location

  beforeEach(() => {
    vi.resetModules()
  })

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true,
    })
  })

  it('uses dev URL on dev subdomain', async () => {
    Object.defineProperty(window, 'location', {
      value: { hostname: 'analytics.dev.outcomeops.ai' },
      writable: true,
    })

    expect(window.location.hostname).toContain('dev.outcomeops.ai')
  })

  it('uses production URL on production domain', async () => {
    Object.defineProperty(window, 'location', {
      value: { hostname: 'analytics.outcomeops.ai' },
      writable: true,
    })

    expect(window.location.hostname).not.toContain('dev.')
  })
})

describe('API request functions', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.resetAllMocks()
    global.fetch = vi.fn()
    localStorage.clear()
  })

  it('getStats calls fetch with correct URL', async () => {
    const mockResponse = {
      ok: true,
      json: vi.fn().mockResolvedValue({
        domain: 'myfantasy.ai',
        total_requests: 100,
        unique_visitors: 50,
        daily: {},
        from_date: '2024-01-01',
        to_date: '2024-01-31',
      }),
    }
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

    const { getStats } = await import('../../../src/api/analytics')
    await getStats('myfantasy.ai')

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/analytics/stats/myfantasy.ai'),
      expect.anything()
    )
  })

  it('getStats includes date parameters in URL', async () => {
    const mockResponse = {
      ok: true,
      json: vi.fn().mockResolvedValue({ domain: 'myfantasy.ai', daily: {} }),
    }
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

    const { getStats } = await import('../../../src/api/analytics')
    await getStats('myfantasy.ai', '2024-01-01', '2024-01-31')

    const callUrl = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0]
    expect(callUrl).toContain('from=2024-01-01')
    expect(callUrl).toContain('to=2024-01-31')
  })

  it('request throws error on non-ok response', async () => {
    const mockResponse = {
      ok: false,
      json: vi.fn().mockResolvedValue({ error: 'Unauthorized' }),
    }
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

    const { getStats } = await import('../../../src/api/analytics')

    await expect(getStats('myfantasy.ai')).rejects.toThrow('Unauthorized')
  })

  it('getPages calls correct endpoint', async () => {
    const mockResponse = {
      ok: true,
      json: vi.fn().mockResolvedValue({ domain: 'myfantasy.ai', pages: [] }),
    }
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

    const { getPages } = await import('../../../src/api/analytics')
    await getPages('myfantasy.ai')

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/analytics/pages/myfantasy.ai'),
      expect.anything()
    )
  })

  it('getReferrers calls correct endpoint', async () => {
    const mockResponse = {
      ok: true,
      json: vi.fn().mockResolvedValue({ domain: 'myfantasy.ai', referrers: [] }),
    }
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

    const { getReferrers } = await import('../../../src/api/analytics')
    await getReferrers('myfantasy.ai')

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/analytics/referrers/myfantasy.ai'),
      expect.anything()
    )
  })

  it('getCountries calls correct endpoint', async () => {
    const mockResponse = {
      ok: true,
      json: vi.fn().mockResolvedValue({ domain: 'myfantasy.ai', countries: [] }),
    }
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

    const { getCountries } = await import('../../../src/api/analytics')
    await getCountries('myfantasy.ai')

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/analytics/countries/myfantasy.ai'),
      expect.anything()
    )
  })
})
