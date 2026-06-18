import assert from 'node:assert/strict'
import test from 'node:test'

import { detectPatternSpans } from '../src/services/piiPatterns.ts'

function detectedValues(text, tag) {
  return detectPatternSpans(text)
    .filter((span) => span.tag === tag)
    .map((span) => text.slice(span.start, span.end))
}

test('detects complete email addresses instead of only their handles', () => {
  const text = 'Email alex.smith+help@example.co.uk today.'

  assert.deepEqual(detectedValues(text, 'EMAIL'), [
    'alex.smith+help@example.co.uk',
  ])
})

test('detects international, local, and parenthesized phone numbers', () => {
  const text =
    'Call +357 99 123 456, 99123456, or (202) 555-0182. Not 2026-06-15.'

  assert.deepEqual(detectedValues(text, 'PHONE'), [
    '+357 99 123 456',
    '99123456',
    '(202) 555-0182',
  ])
})

test('detects common numbered street addresses and PO boxes', () => {
  const text =
    'Send it to 42B Makariou III Avenue, or P.O. Box 1234. Meet at 10 Rue de la Paix.'

  assert.deepEqual(detectedValues(text, 'ADDRESS'), [
    'P.O. Box 1234',
    '42B Makariou III Avenue',
    '10 Rue de la Paix',
  ])
})

test('keeps match offsets correct for multiline Unicode text', () => {
  const text =
    'Στοιχεία:\nοδός: 12 Αρχιεπισκόπου Μακαρίου Avenue\nemail@example.com'
  const spans = detectPatternSpans(text)

  for (const span of spans) {
    assert.ok(span.start >= 0)
    assert.ok(span.end <= text.length)
    assert.ok(text.slice(span.start, span.end).length > 0)
  }

  assert.deepEqual(detectedValues(text, 'ADDRESS'), [
    '12 Αρχιεπισκόπου Μακαρίου Avenue',
  ])
  assert.deepEqual(detectedValues(text, 'EMAIL'), ['email@example.com'])
})
