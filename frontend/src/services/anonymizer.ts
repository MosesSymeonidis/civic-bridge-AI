import type { TokenClassificationPipeline } from '@huggingface/transformers'
import { detectPatternSpans } from './piiPatterns'

const PII_MODEL_ID =
  'onnx-community/piiranha-v1-detect-personal-information-ONNX'
const NAME_MODEL_ID =
  'onnx-community/bert-base-multilingual-cased-ner-hrl-ONNX'
const CHUNK_SIZE = 800
const NAME_SCORE_THRESHOLD = 0.5

type SessionState = {
  counters: Record<string, number>
  seen: Map<string, string>
}

type TextChunk = {
  offset: number
  text: string
}

type EntitySpan = {
  start: number
  end: number
  tag: string
}

let piiPromise: Promise<TokenClassificationPipeline> | null = null
let namePromise: Promise<TokenClassificationPipeline> | null = null
const sessionStates = new Map<string, SessionState>()

function loadPipeline(modelId: string): Promise<TokenClassificationPipeline> {
  return import('@huggingface/transformers')
    .then(({ pipeline }) =>
      pipeline('token-classification', modelId, {
        dtype: 'q8',
      }),
    )
}

function getPii(): Promise<TokenClassificationPipeline> {
  if (!piiPromise) {
    piiPromise = loadPipeline(PII_MODEL_ID)
      .catch((error: unknown) => {
        piiPromise = null
        throw error
      })
  }

  return piiPromise
}

function getNameNer(): Promise<TokenClassificationPipeline> {
  if (!namePromise) {
    namePromise = loadPipeline(NAME_MODEL_ID)
      .catch((error: unknown) => {
        namePromise = null
        throw error
      })
  }

  return namePromise
}

function getSessionState(sessionId: string): SessionState {
  let state = sessionStates.get(sessionId)

  if (!state) {
    state = {
      counters: {},
      seen: new Map<string, string>(),
    }
    sessionStates.set(sessionId, state)
  }

  return state
}

function placeholder(value: string, tag: string, state: SessionState): string {
  const key = value.toLowerCase().trim()
  const existing = state.seen.get(key)

  if (existing) {
    return existing
  }

  state.counters[tag] = (state.counters[tag] ?? 0) + 1
  const replacement = `[${tag}_${state.counters[tag]}]`
  state.seen.set(key, replacement)
  return replacement
}

function chunks(text: string): TextChunk[] {
  const output: TextChunk[] = []

  for (let offset = 0; offset < text.length; offset += CHUNK_SIZE) {
    output.push({
      offset,
      text: text.slice(offset, offset + CHUNK_SIZE),
    })
  }

  return output
}

function normalizeTag(tag: string): string {
  const normalized = Array.from(tag.toUpperCase(), (character) => {
    const code = character.charCodeAt(0)
    const isLetter = code >= 65 && code <= 90
    const isDigit = code >= 48 && code <= 57
    return isLetter || isDigit || character === '_' ? character : '_'
  }).join('')
  return normalized || 'PII'
}

function findDetectedText(
  text: string,
  detectedText: string,
  searchFrom: number,
): { start: number; end: number } | null {
  const exactStart = text.indexOf(detectedText, searchFrom)
  if (exactStart >= 0) {
    return {
      start: exactStart,
      end: exactStart + detectedText.length,
    }
  }

  for (let start = searchFrom; start < text.length; start += 1) {
    let sourceIndex = start
    let detectedIndex = 0

    while (
      sourceIndex < text.length &&
      text[sourceIndex].trim() === ''
    ) {
      sourceIndex += 1
    }
    const matchStart = sourceIndex

    while (
      sourceIndex < text.length &&
      detectedIndex < detectedText.length
    ) {
      if (text[sourceIndex].trim() === '') {
        sourceIndex += 1
        continue
      }

      if (detectedText[detectedIndex].trim() === '') {
        detectedIndex += 1
        continue
      }

      if (text[sourceIndex] !== detectedText[detectedIndex]) {
        break
      }

      sourceIndex += 1
      detectedIndex += 1
    }

    while (
      detectedIndex < detectedText.length &&
      detectedText[detectedIndex].trim() === ''
    ) {
      detectedIndex += 1
    }

    if (detectedIndex === detectedText.length) {
      return { start: matchStart, end: sourceIndex }
    }
  }

  return null
}

function addSpan(
  spans: EntitySpan[],
  chunk: TextChunk,
  start: number | undefined,
  end: number | undefined,
  word: string,
  tag: string,
  searchFrom: number,
): number {
  let spanStart = start
  let spanEnd = end

  if (
    spanStart === undefined ||
    spanEnd === undefined ||
    spanStart < 0 ||
    spanEnd <= spanStart ||
    spanEnd > chunk.text.length
  ) {
    const detectedText = word.trim()
    const match =
      findDetectedText(chunk.text, detectedText, searchFrom) ??
      findDetectedText(chunk.text, detectedText, 0)

    if (!match || !detectedText) {
      return searchFrom
    }

    spanStart = match.start
    spanEnd = match.end
  }

  spans.push({
    start: chunk.offset + spanStart,
    end: chunk.offset + spanEnd,
    tag,
  })

  return spanEnd
}

function mergeOverlappingSpans(spans: EntitySpan[]): EntitySpan[] {
  spans.sort(
    (left, right) =>
      left.start - right.start ||
      right.end - right.start - (left.end - left.start),
  )

  const merged: EntitySpan[] = []

  for (const span of spans) {
    const previous = merged.at(-1)

    if (!previous || span.start >= previous.end) {
      merged.push({ ...span })
      continue
    }

    previous.end = Math.max(previous.end, span.end)
  }

  return merged
}

async function detectSpans(text: string): Promise<EntitySpan[]> {
  const [pii, nameNer] = await Promise.all([getPii(), getNameNer()])
  const spans: EntitySpan[] = detectPatternSpans(text)

  for (const chunk of chunks(text)) {
    const piiEntities = await pii(chunk.text, {
      aggregation_strategy: 'simple',
    })
    let piiSearchFrom = 0

    for (const entity of piiEntities) {
      piiSearchFrom = addSpan(
        spans,
        chunk,
        entity.start,
        entity.end,
        entity.word,
        normalizeTag(entity.entity_group),
        piiSearchFrom,
      )
    }

    const nameEntities = await nameNer(chunk.text, {
      aggregation_strategy: 'simple',
    })
    let nameSearchFrom = 0

    for (const entity of nameEntities) {
      if (
        entity.entity_group.toUpperCase() !== 'PER' ||
        entity.score <= NAME_SCORE_THRESHOLD
      ) {
        continue
      }

      nameSearchFrom = addSpan(
        spans,
        chunk,
        entity.start,
        entity.end,
        entity.word,
        'PERSON',
        nameSearchFrom,
      )
    }
  }

  return mergeOverlappingSpans(spans)
}

export async function anonymizeChatMessage(
  text: string,
  sessionId: string,
): Promise<string> {
  const state = getSessionState(sessionId)
  let output = text
  const spans = await detectSpans(text)

  spans.sort((left, right) => right.start - left.start || right.end - left.end)

  let nextStart = output.length
  for (const span of spans) {
    const value = output.slice(span.start, span.end)

    if (span.end > nextStart || !value.trim()) {
      continue
    }

    output =
      output.slice(0, span.start) +
      placeholder(value, span.tag, state) +
      output.slice(span.end)
    nextStart = span.start
  }

  return output
}

export function preloadAnonymizer(): Promise<void> {
  return Promise.all([getPii(), getNameNer()]).then(() => undefined)
}

export function clearAnonymizationSession(sessionId: string): void {
  sessionStates.delete(sessionId)
}
