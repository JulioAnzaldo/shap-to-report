import type { SituationalReport } from '../types'

const DEGRADED_LABELS: Record<string, { title: string; color: string; icon: string }> = {
  insufficient_context_retrieval: {
    title: 'Insufficient Context',
    color: '#fbbf24',
    icon: '⚠',
  },
  model_low_confidence: {
    title: 'Low Confidence',
    color: '#60a5fa',
    icon: '◌',
  },
  validation_failed: {
    title: 'Validation Failed',
    color: '#f87171',
    icon: '✕',
  },
  llm_unavailable: {
    title: 'LLM Unavailable',
    color: '#f87171',
    icon: '✕',
  },
  shap_unavailable: {
    title: 'SHAP Unavailable',
    color: '#6b6b7e',
    icon: '—',
  },
}

interface Props {
  report: SituationalReport
}

export function RefusalCard({ report }: Props) {
  const meta = DEGRADED_LABELS[report.degraded_mode] ?? {
    title: report.degraded_mode,
    color: '#6b6b7e',
    icon: '—',
  }

  return (
    <div
      style={{
        margin: '32px auto',
        maxWidth: 560,
        borderRadius: 16,
        border: `1px solid ${meta.color}30`,
        background: `${meta.color}08`,
        padding: '32px',
        textAlign: 'center',
      }}
    >
      <div
        style={{
          width: 48,
          height: 48,
          borderRadius: '50%',
          border: `1px solid ${meta.color}40`,
          background: `${meta.color}15`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 20,
          color: meta.color,
          margin: '0 auto 16px',
        }}
      >
        {meta.icon}
      </div>

      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: meta.color,
          marginBottom: 8,
        }}
      >
        {meta.title}
      </div>

      <div
        style={{
          fontSize: 13,
          color: 'var(--color-text-muted)',
          lineHeight: 1.6,
          maxWidth: 400,
          margin: '0 auto',
        }}
      >
        {report.refusal_reason ?? 'Report generation was halted before completion.'}
      </div>

      {report.degraded_mode === 'model_low_confidence' && report.confidence != null && (
        <div
          style={{
            marginTop: 20,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            padding: '6px 14px',
            borderRadius: 20,
            background: 'rgba(96,165,250,0.1)',
            border: '1px solid rgba(96,165,250,0.2)',
          }}
        >
          <span style={{ fontSize: 11, color: '#60a5fa' }}>
            Confidence: {(report.confidence * 100).toFixed(0)}%
          </span>
        </div>
      )}
    </div>
  )
}
