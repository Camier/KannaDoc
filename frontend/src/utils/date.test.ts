import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getTimeLabel } from './date';

describe('getTimeLabel', () => {
  beforeEach(() => {
    // Tell Vitest use fake timers
    vi.useFakeTimers();
  });

  afterEach(() => {
    // restoring date after each test run
    vi.useRealTimers();
  });

  it('should return "today" for current date', () => {
    // Mock date to 2026-01-24 10:00:00 UTC
    const mockNow = new Date('2026-01-24T10:00:00Z');
    vi.setSystemTime(mockNow);

    // Beijing time would be 2026-01-24 18:00:00
    // If lastModifyAt is also today (UTC), it should be today
    expect(getTimeLabel('2026-01-24T10:00:00Z')).toBe('today');
  });

  it('should return "yesterday" for a date 24 hours ago', () => {
    const mockNow = new Date('2026-01-24T10:00:00Z');
    vi.setSystemTime(mockNow);

    // 24 hours ago: 2026-01-23 10:00:00 UTC
    expect(getTimeLabel('2026-01-23T10:00:00Z')).toBe('yesterday');
  });

  it('should return "within_7_days" for a date 3 days ago', () => {
    const mockNow = new Date('2026-01-24T10:00:00Z');
    vi.setSystemTime(mockNow);

    expect(getTimeLabel('2026-01-21T10:00:00Z')).toBe('within_7_days');
  });

  it('should return "within_30_days" for a date 15 days ago', () => {
    const mockNow = new Date('2026-01-24T10:00:00Z');
    vi.setSystemTime(mockNow);

    expect(getTimeLabel('2026-01-09T10:00:00Z')).toBe('within_30_days');
  });

  it('should return "earlier" for a date 2 months ago', () => {
    const mockNow = new Date('2026-01-24T10:00:00Z');
    vi.setSystemTime(mockNow);

    expect(getTimeLabel('2025-11-24T10:00:00Z')).toBe('earlier');
  });
});
