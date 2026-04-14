import { describe, it, expect } from 'vitest'
import { emailSnippetToCustomerPlainText } from '../utils/emailPlainText'

describe('emailSnippetToCustomerPlainText', () => {
  it('strips truncated Outlook mobile wrapper (no closing >)', () => {
    const raw = '<div id="ms-outlook-mobile-body-" dir="ltr"'
    const out = emailSnippetToCustomerPlainText(raw, { maxLen: 200 })
    expect(out).not.toMatch(/</)
    expect(out).not.toMatch(/DOCTYPE|ms-outlook|dir=/)
  })

  it('strips truncated meta tag', () => {
    const raw = '<meta name=robots content="noindex"'
    const out = emailSnippetToCustomerPlainText(raw, { maxLen: 200 })
    expect(out).not.toMatch(/</)
    expect(out).not.toMatch(/meta|robots/)
  })

  it('keeps real sentence after removing leading tag junk', () => {
    const raw =
      '<div id="x">Hello, I would like to discuss pricing.</div>'
    const out = emailSnippetToCustomerPlainText(raw, { maxLen: 200 })
    expect(out.toLowerCase()).toContain('pricing')
    expect(out).not.toMatch(/<div/)
  })
})
