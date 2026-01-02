import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import StatsCards from '../../../src/components/StatsCards'
import { StatsResponse } from '../../../src/api/analytics'

describe('StatsCards', () => {
  const createMockStats = (overrides: Partial<StatsResponse> = {}): StatsResponse => ({
    domain: 'myfantasy.ai',
    from_date: '2024-01-01',
    to_date: '2024-01-31',
    total_requests: 1000,
    unique_visitors: 500,
    daily: {
      '2024-01-01': 100,
      '2024-01-02': 150,
    },
    ...overrides,
  })

  it('renders stats correctly', () => {
    const stats = createMockStats({
      total_requests: 1000,
      unique_visitors: 250,  // Different value to avoid collision with avg
    })
    render(<StatsCards stats={stats} />)

    expect(screen.getByText('1,000')).toBeInTheDocument()
    expect(screen.getByText('250')).toBeInTheDocument()
  })

  it('handles zero values', () => {
    const stats = createMockStats({
      total_requests: 0,
      unique_visitors: 0,
      daily: {},
    })
    render(<StatsCards stats={stats} />)

    expect(screen.getAllByText('0').length).toBeGreaterThan(0)
  })

  it('formats large numbers with commas', () => {
    const stats = createMockStats({
      total_requests: 1234567,
      unique_visitors: 987654,
    })
    render(<StatsCards stats={stats} />)

    expect(screen.getByText('1,234,567')).toBeInTheDocument()
    expect(screen.getByText('987,654')).toBeInTheDocument()
  })

  it('shows appropriate labels', () => {
    const stats = createMockStats()
    render(<StatsCards stats={stats} />)

    expect(screen.getByText('Total Requests')).toBeInTheDocument()
    expect(screen.getByText('Unique Visitors')).toBeInTheDocument()
    expect(screen.getByText('Days Tracked')).toBeInTheDocument()
    expect(screen.getByText('Avg Daily Requests')).toBeInTheDocument()
  })

  it('calculates days tracked correctly', () => {
    const stats = createMockStats({
      daily: {
        '2024-01-01': 100,
        '2024-01-02': 150,
        '2024-01-03': 200,
      },
    })
    render(<StatsCards stats={stats} />)

    expect(screen.getByText('3')).toBeInTheDocument() // 3 days
  })

  it('calculates average daily requests', () => {
    const stats = createMockStats({
      total_requests: 300,
      daily: {
        '2024-01-01': 100,
        '2024-01-02': 100,
        '2024-01-03': 100,
      },
    })
    render(<StatsCards stats={stats} />)

    expect(screen.getByText('100')).toBeInTheDocument() // 300/3 = 100
  })
})
