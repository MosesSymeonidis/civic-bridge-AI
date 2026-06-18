export type PatternSpan = {
  start: number
  end: number
  tag: string
}

type PatternRule = {
  tag: string
  pattern: RegExp
  isValid?: (value: string) => boolean
}

const ADDRESS_WORD = String.raw`[\p{L}\p{M}][\p{L}\p{M}\p{N}.'’\-]*`
const STREET_SUFFIX = String.raw`(?:street|st|road|rd|avenue|ave|boulevard|blvd|lane|ln|drive|dr|court|ct|place|pl|square|sq|terrace|way|highway|hwy|close|crescent|gardens|parkway|strasse|straße|straat|laan)`
const STREET_PREFIX = String.raw`(?:rue|via|viale|calle|avenida|rua|ulica|ulitsa|ul\.|οδός|οδος|λεωφόρος|λεωφορος|sokak|sokağı|sokagi|cadde|caddesi)`

const ISO_DATE_PATTERN = /^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}$/
const LOCAL_DATE_PATTERN = /^\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}$/
const IPV4_PATTERN = /^(?:\d{1,3}\.){3}\d{1,3}$/
const PHONE_EXTENSION_PATTERN =
  /\s*(?:ext\.?|extension|x)\s*\d{1,6}\s*$/i

function isPhoneNumber(value: string): boolean {
  const number = value.replace(PHONE_EXTENSION_PATTERN, '').trim()
  const digits = number.replace(/\D/g, '')

  return (
    digits.length >= 7 &&
    digits.length <= 15 &&
    !ISO_DATE_PATTERN.test(number) &&
    !LOCAL_DATE_PATTERN.test(number) &&
    !IPV4_PATTERN.test(number)
  )
}

const PATTERN_RULES: PatternRule[] = [
  {
    tag: 'EMAIL',
    pattern:
      /(?<![A-Z0-9.!#$%&'*+/=?^_`{|}~-])[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+(?![A-Z0-9-])/gi,
  },
  {
    tag: 'URL',
    pattern: /https?:\/\/[^\s<>"']+/gi,
  },
  {
    tag: 'PHONE',
    pattern:
      /(?<![\p{L}\p{N}])(?:(?:\+|00)\s*)?(?:\(\d{1,4}\)|\d)(?:[\s().-]*\d){6,14}(?:\s*(?:ext\.?|extension|x)\s*\d{1,6})?(?![\p{L}\p{N}])/giu,
    isValid: isPhoneNumber,
  },
  {
    tag: 'ADDRESS',
    pattern: /\bP\.?\s*O\.?\s+Box\s+\d{1,10}\b/gi,
  },
  {
    tag: 'ADDRESS',
    pattern: new RegExp(
      String.raw`(?<![\p{L}\p{N}])\d{1,5}[\p{L}]?(?:[ \t]*[-/][ \t]*\d{1,5}[\p{L}]?)?[ \t]+(?:${ADDRESS_WORD}[ \t]+){1,6}${STREET_SUFFIX}\.?(?:[ \t]+(?:apartment|apt|flat|unit|suite|floor|fl|no)\.?[ \t]*[\p{L}\p{N}-]+)?`,
      'giu',
    ),
  },
  {
    tag: 'ADDRESS',
    pattern: new RegExp(
      String.raw`(?<![\p{L}\p{N}])\d{1,5}[\p{L}]?[ \t]+${STREET_PREFIX}[ \t]+${ADDRESS_WORD}(?:[ \t]+${ADDRESS_WORD}){0,4}`,
      'giu',
    ),
  },
  {
    tag: 'ADDRESS',
    pattern: new RegExp(
      String.raw`\b${STREET_PREFIX}[ \t]+${ADDRESS_WORD}(?:[ \t]+${ADDRESS_WORD}){0,4}[ \t]+\d{1,5}[\p{L}]?\b`,
      'giu',
    ),
  },
  {
    tag: 'HANDLE',
    pattern:
      /(?<![\p{L}\p{N}._%+-])@[\p{L}\p{N}_](?:[\p{L}\p{N}_.-]{0,29}[\p{L}\p{N}_])?/gu,
  },
]

function trimTrailingPunctuation(
  text: string,
  start: number,
  end: number,
): number {
  let trimmedEnd = end

  while (trimmedEnd > start && /[.,;:!?]/.test(text[trimmedEnd - 1])) {
    trimmedEnd -= 1
  }

  return trimmedEnd
}

export function detectPatternSpans(text: string): PatternSpan[] {
  const spans: PatternSpan[] = []

  for (const rule of PATTERN_RULES) {
    rule.pattern.lastIndex = 0

    for (const match of text.matchAll(rule.pattern)) {
      const value = match[0]
      const start = match.index
      const end = trimTrailingPunctuation(text, start, start + value.length)
      const trimmedValue = text.slice(start, end)

      if (end <= start || (rule.isValid && !rule.isValid(trimmedValue))) {
        continue
      }

      spans.push({ start, end, tag: rule.tag })
    }
  }

  return spans
}
