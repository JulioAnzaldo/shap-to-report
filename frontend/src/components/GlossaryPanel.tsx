import { useState } from 'react'
import type { ProvenanceEntry } from '../types'

interface Props {
  activeChunk: (ProvenanceEntry & { fullText?: string }) | null
  onClose: () => void
}

const TERMS: { term: string; def: string }[] = [
  {
    term: 'SHAP',
    def: 'SHapley Additive exPlanations — a game-theory method that assigns each feature a contribution score explaining how much it pushed the anomaly score up or down.',
  },
  {
    term: 'Gini coefficient',
    def: 'Measures how concentrated the SHAP attribution is. 0 = perfectly diffuse (all features equal). 1 = fully concentrated (one feature dominates). High Gini → easier to diagnose.',
  },
  {
    term: 'Ensemble agreement',
    def: 'How many of the anomaly detection models flagged this window. 3/3 = all models agree. 1/3 = only one model flagged it — lower confidence.',
  },
  {
    term: 'Ensemble score',
    def: 'Normalized anomaly score from the ensemble [0–1]. Higher = more anomalous. Scores above 0.7 are typically considered significant.',
  },
  {
    term: 'Degraded mode',
    def: 'When the pipeline cannot produce a confident report, it returns a structured refusal with a reason code instead of generating potentially unreliable output.',
  },
  {
    term: 'Provenance',
    def: 'The retrieved regulatory or historical chunks that grounded the report. Every claim in the explanation should trace back to a provenance entry.',
  },
  {
    term: 'Attribution concentration',
    def: 'Same as Gini coefficient — stored in the report alongside the raw SHAP values for reference.',
  },
  {
    term: 'Point anomaly',
    def: 'A single isolated spike or dropout in the telemetry signal. Typically caused by a transient fault, bit flip, or sensor glitch.',
  },
  {
    term: 'Contextual anomaly',
    def: 'A value that is normal in isolation but anomalous given the surrounding context — e.g., a reading that is normal at one mission phase but not another.',
  },
  {
    term: 'Window',
    def: 'A fixed-length slice of the telemetry time series (50 samples by default) over which SHAP features are computed. The window start index locates it in the full channel.',
  },
  {
    term: 'mean / std / min / max / slope',
    def: 'The 5 statistical features computed over each telemetry window. SHAP attribution is over these statistics of the primary channel (ch_00), not the raw sensor values.',
  },
  {
    term: 'SMAP channel prefixes',
    def: 'Channel IDs in the Hundman et al. (KDD 2018) dataset are anonymized. The first letter indicates subsystem type: P = power, R = radiation, T = thermal, A = attitude control (likely), D = data/downlink (likely), E = electrical, F = fault/flag, G = guidance. The 25 input columns per channel are: col 0 = the monitored telemetry value (pre-scaled to [-1,1]); cols 1–24 = one-hot encoded command flags indicating which spacecraft commands were active in that time window. Column names are not publicly released.',
  },
  {
    term: 'Perturbation attribution',
    def: 'A model-agnostic method: for each input channel, replace it with its training mean and measure how much the anomaly score drops. A large drop means that channel contributed significantly to the anomaly. This is a proxy for SHAP over raw channels — GDN/TrAD will provide proper inter-sensor attribution.',
  },
  {
    term: 'ch_00 vs ch_01–ch_24',
    def: 'ch_00 is the primary telemetry value being monitored (e.g., a power reading, temperature, or attitude measurement). ch_01 through ch_24 are binary command flags — they encode which spacecraft commands were sent or received during the window. Most anomalies manifest primarily in ch_00; the command flags provide operational context.',
  },
]

const SOURCE_COLOR: Record<string, string> = {
  EU_AI_Act: '#a78bfa',
  NASA_NPR: '#7dd3fc',
  NASA_Lessons_Learned: '#4ade80',
}

export function GlossaryPanel({ activeChunk, onClose }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null)

  return (
    <aside
      style={{
        width: activeChunk ? 320 : 220,
        flexShrink: 0,
        borderLeft: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto',
        background: 'var(--color-surface)',
        transition: 'width 0.2s ease',
      }}
    >
      {/* Chunk viewer */}
      {activeChunk && (
        <div
          style={{
            borderBottom: '1px solid var(--color-border)',
            padding: '14px 16px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 10 }}>
            <div>
              <div
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  color: SOURCE_COLOR[activeChunk.source_body] ?? '#a0a0b8',
                  marginBottom: 3,
                }}
              >
                {activeChunk.source_body.replace(/_/g, ' ')}
              </div>
              <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--color-text)', lineHeight: 1.4 }}>
                {activeChunk.document}
              </div>
              <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 2 }}>
                {activeChunk.section}
              </div>
            </div>
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--color-text-dim)',
                cursor: 'pointer',
                fontSize: 16,
                lineHeight: 1,
                padding: '0 0 0 8px',
                flexShrink: 0,
              }}
            >
              ×
            </button>
          </div>

          <div
            style={{
              fontSize: 12,
              color: 'var(--color-text-muted)',
              lineHeight: 1.7,
              padding: '10px 12px',
              borderRadius: 8,
              background: 'var(--color-surface-2)',
              border: '1px solid var(--color-border)',
              maxHeight: 280,
              overflowY: 'auto',
            }}
          >
            {activeChunk.fullText ?? '(Full text not available — chunk text is in the retrieved context)'}
          </div>

          <div
            style={{
              marginTop: 8,
              fontSize: 11,
              color: 'var(--color-text-dim)',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: SOURCE_COLOR[activeChunk.source_body] ?? '#a0a0b8',
                display: 'inline-block',
              }}
            />
            Relevance: {Math.round(activeChunk.relevance_score * 100)}%
          </div>
        </div>
      )}

      {/* Glossary header */}
      <div
        style={{
          padding: '14px 16px 10px',
          borderBottom: '1px solid var(--color-border)',
        }}
      >
        <div
          style={{
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: '0.1em',
            color: 'var(--color-text-dim)',
            textTransform: 'uppercase',
          }}
        >
          Glossary
        </div>
        <div style={{ fontSize: 11, color: 'var(--color-text-dim)', marginTop: 2 }}>
          Click a term to expand
        </div>
      </div>

      {/* Terms */}
      <div style={{ flex: 1, padding: '6px 0' }}>
        {TERMS.map(({ term, def }) => {
          const open = expanded === term
          return (
            <div key={term} style={{ borderBottom: '1px solid var(--color-border)' }}>
              <button
                onClick={() => setExpanded(open ? null : term)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '9px 16px',
                  background: open ? 'rgba(167,139,250,0.06)' : 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  textAlign: 'left',
                  gap: 8,
                }}
              >
                <span
                  style={{
                    fontSize: 12,
                    fontWeight: open ? 500 : 400,
                    color: open ? 'var(--color-accent)' : 'var(--color-text-muted)',
                  }}
                >
                  {term}
                </span>
                <span style={{ fontSize: 10, color: 'var(--color-text-dim)', flexShrink: 0 }}>
                  {open ? '▲' : '▼'}
                </span>
              </button>
              {open && (
                <div
                  style={{
                    padding: '0 16px 10px',
                    fontSize: 11,
                    color: 'var(--color-text-muted)',
                    lineHeight: 1.6,
                  }}
                >
                  {def}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </aside>
  )
}
