import { type ChangeEvent, useState } from 'react'
import Papa from 'papaparse'

import {
  anonymizeChatMessage,
  clearAnonymizationSession,
  preloadAnonymizer,
} from '../services/anonymizer'
import { analyzeSocialMediaPost } from '../services/chatAnalysis'
import { classifySemanticCluster } from '../services/semanticClustering'
import {
  type SocialMediaCsvRow,
  findExistingSocialMediaPosts,
  storeSocialMediaImport,
} from '../services/socialMediaImports'
import { createUuid } from '../services/uuid'

type SocialMediaCsvImportProps = {
  apiBaseUrl: string
  ragApiBaseUrl: string
  classifierApiBaseUrl: string
  onClose: () => void
  onImported: () => void
}

type ProcessingStage =
  | 'anonymizing'
  | 'analyzing'
  | 'classifying'
  | 'storing'

type ResultStatus = 'imported' | 'duplicate' | 'failed'

type ImportResult = {
  postId: string
  status: ResultStatus
  message?: string
}

type ImportProgress = {
  phase: 'ready' | 'checking' | 'processing' | 'complete'
  total: number
  processed: number
  imported: number
  duplicates: number
  failed: number
  currentPostId?: string
  currentStage?: ProcessingStage
}

const requiredFields = ['post_id', 'post_text', 'country', 'language'] as const
const fieldLengthLimits: Array<[keyof SocialMediaCsvRow, number]> = [
  ['post_id', 200],
  ['post_text', 4000],
  ['country', 100],
  ['language', 80],
  ['region_area', 120],
  ['platform', 80],
  ['source_reference', 200],
]
const maximumRows = 10_000
const maximumFileMegabytes = 50
const maximumFileBytes = maximumFileMegabytes * 1024 * 1024
const recentResultLimit = 100

function statusLabel(status: ProcessingStage | ResultStatus): string {
  return {
    anonymizing: 'Anonymizing locally',
    analyzing: 'Analyzing incident',
    classifying: 'Classifying semantics',
    storing: 'Saving structured results',
    imported: 'Imported',
    duplicate: 'Skipped duplicate',
    failed: 'Failed',
  }[status]
}

function readyProgress(total: number): ImportProgress {
  return {
    phase: 'ready',
    total,
    processed: 0,
    imported: 0,
    duplicates: 0,
    failed: 0,
  }
}

function validateRows(
  fields: string[] | undefined,
  rows: SocialMediaCsvRow[],
): string[] {
  const errors: string[] = []
  for (const field of requiredFields) {
    if (!fields?.includes(field)) {
      errors.push(`Missing required column: ${field}`)
    }
  }
  if (rows.length === 0) errors.push('The CSV file contains no data rows.')
  if (rows.length > maximumRows) {
    errors.push(
      `A maximum of ${maximumRows.toLocaleString()} rows can be imported at once.`,
    )
  }

  const seen = new Set<string>()
  rows.forEach((row, index) => {
    const line = index + 2
    for (const field of requiredFields) {
      if (!row[field]?.trim()) {
        errors.push(`Line ${line}: ${field} is required.`)
      }
    }
    for (const [field, maximumLength] of fieldLengthLimits) {
      if ((row[field]?.length ?? 0) > maximumLength) {
        errors.push(
          `Line ${line}: ${field} exceeds ${maximumLength.toLocaleString()} characters.`,
        )
      }
    }
    if ((row.country?.length ?? 0) < 2) {
      errors.push(`Line ${line}: country must contain at least 2 characters.`)
    }
    if ((row.language?.length ?? 0) < 2) {
      errors.push(`Line ${line}: language must contain at least 2 characters.`)
    }
    if (seen.has(row.post_id)) {
      errors.push(`Line ${line}: duplicate post_id in this file.`)
    }
    seen.add(row.post_id)
    if (
      row.published_at &&
      Number.isNaN(Date.parse(row.published_at))
    ) {
      errors.push(`Line ${line}: published_at is not a valid timestamp.`)
    }
  })
  return errors.slice(0, 20)
}

function SocialMediaCsvImport({
  apiBaseUrl,
  ragApiBaseUrl,
  classifierApiBaseUrl,
  onClose,
  onImported,
}: SocialMediaCsvImportProps) {
  const [fileName, setFileName] = useState('')
  const [rows, setRows] = useState<SocialMediaCsvRow[]>([])
  const [progress, setProgress] = useState<ImportProgress | null>(null)
  const [recentResults, setRecentResults] = useState<ImportResult[]>([])
  const [errors, setErrors] = useState<string[]>([])
  const [isProcessing, setIsProcessing] = useState(false)

  function updateActivity(postId: string, stage: ProcessingStage) {
    setProgress((current) =>
      current
        ? {
            ...current,
            phase: 'processing',
            currentPostId: postId,
            currentStage: stage,
          }
        : current,
    )
  }

  function recordResult(result: ImportResult) {
    setProgress((current) => {
      if (!current) return current
      return {
        ...current,
        processed: current.processed + 1,
        imported:
          current.imported + (result.status === 'imported' ? 1 : 0),
        duplicates:
          current.duplicates + (result.status === 'duplicate' ? 1 : 0),
        failed: current.failed + (result.status === 'failed' ? 1 : 0),
        currentPostId: undefined,
        currentStage: undefined,
      }
    })
    setRecentResults((current) =>
      [...current, result].slice(-recentResultLimit),
    )
  }

  function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    setRows([])
    setProgress(null)
    setRecentResults([])
    setErrors([])
    setFileName(file?.name ?? '')
    if (!file) return
    if (file.size > maximumFileBytes) {
      setErrors([
        `The CSV file must be ${maximumFileMegabytes} MB or smaller.`,
      ])
      return
    }

    Papa.parse<SocialMediaCsvRow>(file, {
      header: true,
      skipEmptyLines: 'greedy',
      transformHeader: (header) => header.trim().toLowerCase(),
      transform: (value) => value.trim(),
      complete: (result) => {
        const parseErrors = result.errors.map(
          (error) =>
            error.row === undefined
              ? `CSV: ${error.message}`
              : `CSV line ${error.row + 2}: ${error.message}`,
        )
        const validationErrors = validateRows(
          result.meta.fields,
          result.data,
        )
        const allErrors = [...parseErrors, ...validationErrors].slice(0, 20)
        setErrors(allErrors)
        if (allErrors.length === 0) {
          setRows(result.data)
          setProgress(readyProgress(result.data.length))
          void preloadAnonymizer().catch(() => undefined)
        }
      },
      error: (error) => setErrors([error.message]),
    })
  }

  async function processRows() {
    if (rows.length === 0 || isProcessing) return

    setIsProcessing(true)
    setErrors([])
    setRecentResults([])
    setProgress({
      ...readyProgress(rows.length),
      phase: 'checking',
    })
    let importedCount = 0
    try {
      const existing = await findExistingSocialMediaPosts(
        apiBaseUrl,
        rows.map((row) => row.post_id),
      )
      const duplicateRows = rows.filter((row) => existing.has(row.post_id))
      const pendingRows = rows.filter((row) => !existing.has(row.post_id))

      setProgress({
        phase: pendingRows.length === 0 ? 'complete' : 'processing',
        total: rows.length,
        processed: duplicateRows.length,
        imported: 0,
        duplicates: duplicateRows.length,
        failed: 0,
      })
      setRecentResults(
        duplicateRows.slice(-recentResultLimit).map((row) => ({
          postId: row.post_id,
          status: 'duplicate',
        })),
      )

      for (const row of pendingRows) {
        const anonymizationId = `csv-import:${createUuid()}`
        try {
          updateActivity(row.post_id, 'anonymizing')
          const anonymizedText = await anonymizeChatMessage(
            row.post_text,
            anonymizationId,
          )
          if (!anonymizedText.trim()) {
            throw new Error('Anonymization produced empty content.')
          }

          updateActivity(row.post_id, 'analyzing')
          const analysis = await analyzeSocialMediaPost(
            ragApiBaseUrl,
            anonymizedText,
            row.country,
          )
          updateActivity(row.post_id, 'classifying')
          const classification = await classifySemanticCluster(
            classifierApiBaseUrl,
            anonymizedText,
          )
          updateActivity(row.post_id, 'storing')
          const status = await storeSocialMediaImport(
            apiBaseUrl,
            row,
            anonymizedText,
            analysis,
            classification,
            { notifyDashboard: false },
          )
          if (status === 'imported') importedCount += 1
          recordResult({ postId: row.post_id, status })
        } catch (error) {
          recordResult({
            postId: row.post_id,
            status: 'failed',
            message:
              error instanceof Error ? error.message : 'Import failed.',
          })
        } finally {
          clearAnonymizationSession(anonymizationId)
        }
      }
      setProgress((current) =>
        current
          ? {
              ...current,
              phase: 'complete',
              currentPostId: undefined,
              currentStage: undefined,
            }
          : current,
      )
    } catch (error) {
      setErrors([
        error instanceof Error
          ? error.message
          : 'The import could not be started.',
      ])
      setProgress((current) =>
        current ? { ...readyProgress(current.total) } : current,
      )
    } finally {
      setIsProcessing(false)
      if (importedCount > 0) onImported()
    }
  }

  const processedPercentage =
    progress && progress.total > 0
      ? Math.round((progress.processed / progress.total) * 100)
      : 0
  const isChecking = progress?.phase === 'checking'
  const progressMessage =
    progress?.phase === 'checking'
      ? 'Checking existing post IDs in batches...'
      : progress?.currentPostId && progress.currentStage
        ? `${statusLabel(progress.currentStage)}: ${progress.currentPostId}`
        : progress?.phase === 'complete'
          ? `Finished processing ${progress.processed.toLocaleString()} rows.`
          : 'Ready to begin analysis.'

  return (
    <section className="social-import-section" id="social-media-import">
      <header>
        <div>
          <p className="eyebrow">Bulk intake</p>
          <h2>Import social media posts from CSV.</h2>
          <p>
            Posts are processed one at a time. Content is anonymized locally
            before analysis and is never stored by the platform.
          </p>
        </div>
        <button disabled={isProcessing} onClick={onClose} type="button">
          Close importer
        </button>
      </header>

      <div className="social-import-schema">
        <strong>Required columns</strong>
        <code>post_id, post_text, country, language</code>
        <span>
          Optional: region_area, platform, published_at, source_reference
        </span>
      </div>

      <label className="social-import-file">
        <span>{fileName || 'Select a CSV file'}</span>
        <small>
          Maximum {maximumRows.toLocaleString()} rows and{' '}
          {maximumFileMegabytes} MB
        </small>
        <input
          accept=".csv,text/csv"
          disabled={isProcessing}
          onChange={handleFile}
          type="file"
        />
      </label>

      {errors.length > 0 && (
        <div className="social-import-errors" role="alert">
          {errors.map((error) => <p key={error}>{error}</p>)}
        </div>
      )}

      {rows.length > 0 && (
        <>
          <div className="social-import-summary">
            <span>{rows.length.toLocaleString()} rows loaded</span>
            <span>{progress?.imported.toLocaleString() ?? 0} imported</span>
            <span>{progress?.duplicates.toLocaleString() ?? 0} duplicates</span>
            <span>{progress?.failed.toLocaleString() ?? 0} failed</span>
            <button disabled={isProcessing} onClick={processRows} type="button">
              {isProcessing ? 'Processing rows...' : 'Analyze and import'}
            </button>
          </div>

          {progress && (
            <div className="social-import-progress-overview" aria-live="polite">
              <div className="social-import-progress-heading">
                <strong>
                  {isChecking
                    ? 'Preparing import'
                    : `${progress.processed.toLocaleString()} of ${progress.total.toLocaleString()} rows processed`}
                </strong>
                <span>{isChecking ? 'Checking' : `${processedPercentage}%`}</span>
              </div>
              <div
                aria-label="Social media import progress"
                aria-valuemax={progress.total}
                aria-valuemin={0}
                aria-valuenow={isChecking ? undefined : progress.processed}
                className={`social-import-progress-track${isChecking ? ' is-indeterminate' : ''}`}
                role="progressbar"
              >
                <span style={{ width: `${processedPercentage}%` }} />
              </div>
              <p>{progressMessage}</p>
            </div>
          )}

          {recentResults.length > 0 && (
            <div className="social-import-results">
              <div className="social-import-results-heading">
                <strong>Recent results</strong>
                <span>
                  Showing the latest{' '}
                  {Math.min(recentResults.length, recentResultLimit)}
                </span>
              </div>
              <div className="social-import-progress">
                {recentResults.map((row) => (
                  <div
                    className={`social-import-row social-import-row--${row.status}`}
                    key={row.postId}
                  >
                    <strong>{row.postId}</strong>
                    <span>{statusLabel(row.status)}</span>
                    {row.message && <small>{row.message}</small>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  )
}

export default SocialMediaCsvImport
