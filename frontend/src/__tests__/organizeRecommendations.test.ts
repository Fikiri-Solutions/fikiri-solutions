import { describe, it, expect } from 'vitest'
import {
  buildRecommendationGroups,
  cleanupActionUserLabel,
  displayOrganizeReason,
  formatRecommendationSummary,
} from '../constants/organizeRecommendations'

describe('organizeRecommendations', () => {
  it('maps cleanup_action to user-safe labels', () => {
    expect(cleanupActionUserLabel('archive')).toBe('File away in Gmail')
    expect(cleanupActionUserLabel('spam_candidate')).toBe('Report spam')
    expect(cleanupActionUserLabel('delete_candidate')).toBe('Move to trash')
    expect(cleanupActionUserLabel('keep')).toBe('Leave in inbox')
  })

  it('groups selected rows by bulk action', () => {
    const groups = buildRecommendationGroups([
      { id: 'a', cleanup_action: 'archive' },
      { id: 'b', cleanup_action: 'archive' },
      { id: 'c', cleanup_action: 'spam_candidate' },
    ])
    expect(groups).toHaveLength(2)
    expect(groups.find((g) => g.bulkAction === 'archive')?.emailIds).toEqual(['a', 'b'])
    expect(groups.find((g) => g.bulkAction === 'spam_candidate')?.destructive).toBe(true)
  })

  it('safeOnly excludes destructive recommendations', () => {
    const groups = buildRecommendationGroups(
      [
        { id: 'a', cleanup_action: 'archive' },
        { id: 'b', cleanup_action: 'spam_candidate' },
      ],
      { safeOnly: true }
    )
    expect(groups).toHaveLength(1)
    expect(groups[0].bulkAction).toBe('archive')
  })

  it('sanitizes heuristic AI jargon in Why copy', () => {
    const text = displayOrganizeReason(
      {
        reason: 'Heuristic classification (AI unavailable).',
        category: 'review_needed',
        cleanup_action: 'keep',
      },
      'not_sure'
    )
    expect(text).toMatch(/not sure|review/i)
    expect(text.toLowerCase()).not.toContain('heuristic')
    expect(text.toLowerCase()).not.toContain('ai unavailable')
  })

  it('formats apply summary for confirmation', () => {
    const summary = formatRecommendationSummary(
      buildRecommendationGroups([{ id: 'x', cleanup_action: 'archive' }])
    )
    expect(summary).toContain('File away in Gmail')
    expect(summary).toContain('1 message')
  })
})
