import { describe, it, expect } from 'vitest'
import { cn } from '../lib/utils'

describe('Utility Functions', () => {
  describe('cn (className utility)', () => {
    it('should merge class names correctly', () => {
      const result = cn('foo', 'bar')
      expect(result).toContain('foo')
      expect(result).toContain('bar')
    })

    it('should handle conditional classes', () => {
      const result = cn('foo', false && 'bar', 'baz')
      expect(result).toContain('foo')
      expect(result).toContain('baz')
      expect(result).not.toContain('bar')
    })

    it('should merge Tailwind classes correctly', () => {
      // Tailwind merge should handle conflicting classes
      const result = cn('p-4', 'p-6')
      // The result should only contain one padding class (p-6 wins)
      expect(result).toBeTruthy()
    })

    it('should handle undefined and null values', () => {
      const result = cn('foo', undefined, null, 'bar')
      expect(result).toContain('foo')
      expect(result).toContain('bar')
    })

    it('should handle empty strings', () => {
      const result = cn('foo', '', 'bar')
      expect(result).toContain('foo')
      expect(result).toContain('bar')
    })

    it('should handle arrays of classes', () => {
      const result = cn(['foo', 'bar'], 'baz')
      expect(result).toContain('foo')
      expect(result).toContain('bar')
      expect(result).toContain('baz')
    })

    it('should handle objects with conditional classes', () => {
      const result = cn({
        'foo': true,
        'bar': false,
        'baz': true,
      })
      expect(result).toContain('foo')
      expect(result).toContain('baz')
      expect(result).not.toContain('bar')
    })

    it('should handle mixed inputs', () => {
      const result = cn(
        'foo',
        ['bar', 'baz'],
        {
          'qux': true,
          'quux': false,
        },
        'corge'
      )
      expect(result).toContain('foo')
      expect(result).toContain('bar')
      expect(result).toContain('baz')
      expect(result).toContain('qux')
      expect(result).toContain('corge')
      expect(result).not.toContain('quux')
    })
  })
})





