import type { SituationalReport, ProvenanceEntry } from '../types'

interface Props {
  report: SituationalReport
  onChunkSelect?: (entry: ProvenanceEntry) => void
}

const SEVERITY_COLOR: Record<string, string> = {
  low: '#34d399',
  medium: '#fbbf24',
  high: '#f97316',
  critical: '#f87171',
}

const ANOMALY_LABEL: Record<string, string> = {
  sensor_fault: 'Sensor Fault',
  actuator_fault: 'Actuator Fault',
  thermal_anomaly: 'Thermal Anomaly',
  power_anomaly: 'Power Anomaly',
  communication_anomaly: 'Comm Anomaly',
  attitude_anomaly: 'Attitude Anomaly',
  propulsion_anomaly: 'Propulsion Anomaly',
  unknown: 'Unknown',
}

const SOURCE_COLOR: Record<string, string> = {
  EU_AI_Act: '#8b5cf6',
  NASA_NPR: '#60a5fa',
  NASA_Lessons_Learned: '#34d399',
}

export function ReportPanel({ report, onChunkSelect }: Props) {
  const sevColor = SEVERITY_COLOR[report.severity ?? ''] ?? '#6b6b7e'
  const confidence = report.confidence ?? 0
  const gini = report.attribution_concentration ?? 0
  const ensembleRatio = report.ensemble_agreement_ratio ?? 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Top row: type + severity + confidence */}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        {report.anomaly_type && (
          <Chip label={ANOMALY_LABEL[report.anomaly_type] ?? report.anomaly_type} color="#8b5cf6" />
        )}
        {report.severity && (
          <Chip label={report.severity.toUpperCase()} color={sevColor} />
        )}
        <Chip
          label={`Confidence ${(confidence * 100).toFixed(0)}%`}
          color={confidence >= 0.7 ? '#34d399' : confidence >= 0.5 ? '#fbbf24' : '#f87171'}
        />
      </div>

      {/* Signal bars */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 10,
        }}
      >
        <SignalBar label="Confidence" value={confidence} color="#8b5cf6" />
        <SignalBar label="Attribution Conc." value={gini} color="#60a5fa" />
        <SignalBar label="Ensemble Agree." value={ensembleRatio} color="#34d399" />
      </div>

      {/* Primary features */}
      {report.primary_features && report.primary_features.length > 0 && (
        <Section title="Primary Features">
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {report.primary_features.map((f) => (
              <span
                key={f}
                style={{
                  padding: '3px 10px',
                  borderRadius: 20,
                  fontSize: 11,
                  fontFamily: 'var(--font-mono)',
                  background: 'rgba(139,92,246,0.12)',
                  border: '1px solid rgba(139,92,246,0.25)',
                  color: '#a78bfa',
                }}
              >
                {f}
              </span>
            ))}
          </div>
        </Section>
      )}

      {/* Explanation */}
      {report.explanation && (
        <Section title="Explanation">
          <p style={{ fontSize: 14, color: 'var(--color-text)', lineHeight: 1.75 }}>
            {report.explanation}
          </p>
        </Section>
      )}

      {/* Operator assessment */}
      {report.operator_assessment && (
        <Section title="Operator Assessment">
          <p style={{ fontSize: 14, color: 'var(--color-text)', lineHeight: 1.75 }}>
            {report.operator_assessment}
          </p>
        </Section>
      )}

      {/* Operator decision */}
      {report.operator_decision && (
        <Section title="Decision Frame">
          <div
            style={{
              padding: '12px 14px',
              borderRadius: 8,
              background: 'rgba(167,139,250,0.07)',
              border: '1px solid rgba(167,139,250,0.18)',
              fontSize: 14,
              color: 'var(--color-text)',
              lineHeight: 1.75,
            }}
          >
            {report.operator_decision}
          </div>
        </Section>
      )}

      {/* Historical precedent */}
      {report.historical_precedent && (
        <Section title="Historical Precedent">
          <div
            style={{
              padding: '10px 14px',
              borderRadius: 8,
              background: 'rgba(52,211,153,0.06)',
              border: '1px solid rgba(52,211,153,0.15)',
              fontSize: 12,
              color: '#6ee7b7',
              lineHeight: 1.6,
              fontFamily: 'var(--font-mono)',
            }}
          >
            {report.historical_precedent}
          </div>
        </Section>
      )}

      {/* Provenance */}
      {report.provenance && report.provenance.length > 0 && (
        <Section title={`Sources (${report.provenance.length})`}>
          <div style={{ fontSize: 11, color: 'var(--color-text-dim)', marginBottom: 8 }}>
            Click a source to read the full retrieved chunk →
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {report.provenance.map((p, i) => (
              <ProvenanceRow key={i} entry={p} onClick={onChunkSelect} />
            ))}
          </div>
        </Section>
      )}
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      style={{
        borderRadius: 10,
        border: '1px solid var(--color-border)',
        background: 'var(--color-surface-2)',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          padding: '8px 14px',
          borderBottom: '1px solid var(--color-border)',
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          color: 'var(--color-text-dim)',
        }}
      >
        {title}
      </div>
      <div style={{ padding: '12px 14px' }}>{children}</div>
    </div>
  )
}

function Chip({ label, color }: { label: string; color: string }) {
  return (
    <span
      style={{
        padding: '4px 12px',
        borderRadius: 20,
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: '0.05em',
        background: `${color}18`,
        border: `1px solid ${color}35`,
        color,
      }}
    >
      {label}
    </span>
  )
}

function SignalBar({ label, value, color }: { label: string; value: number; color: string }) {
  const pct = Math.min(100, Math.max(0, value * 100))
  return (
    <div
      style={{
        padding: '10px 12px',
        borderRadius: 8,
        background: 'var(--color-surface-2)',
        border: '1px solid var(--color-border)',
      }}
    >
      <div
        style={{
          fontSize: 10,
          color: 'var(--color-text-dim)',
          marginBottom: 6,
          letterSpacing: '0.05em',
          textTransform: 'uppercase',
        }}
      >
        {label}
      </div>
      <div
        style={{
          height: 3,
          borderRadius: 2,
          background: 'var(--color-border)',
          marginBottom: 6,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            background: color,
            borderRadius: 2,
            transition: 'width 0.6s ease',
          }}
        />
      </div>
      <div style={{ fontSize: 16, fontWeight: 600, color, fontFamily: 'var(--font-mono)' }}>
        {value.toFixed(2)}
      </div>
    </div>
  )
}

function ProvenanceRow({ entry, onClick }: { entry: ProvenanceEntry; onClick?: (e: ProvenanceEntry) => void }) {
  const color = SOURCE_COLOR[entry.source_body] ?? '#6b6b7e'
  const pct = Math.round(entry.relevance_score * 100)
  const clickable = !!onClick

  return (
    <div
      onClick={() => onClick?.(entry)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '8px 10px',
        borderRadius: 6,
        background: 'rgba(255,255,255,0.02)',
        border: `1px solid ${clickable ? 'var(--color-border-strong)' : 'var(--color-border)'}`,
        cursor: clickable ? 'pointer' : 'default',
        transition: 'background 0.15s',
      }}
      onMouseEnter={(e) => { if (clickable) (e.currentTarget as HTMLDivElement).style.background = 'rgba(167,139,250,0.07)' }}
      onMouseLeave={(e) => { if (clickable) (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,0.02)' }}
    >
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, color: 'var(--color-text)', fontWeight: 500 }}>
          {entry.document}
        </div>
        <div style={{ fontSize: 11, color: 'var(--color-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {entry.section}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
        <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color }}>{pct}%</span>
        {clickable && <span style={{ fontSize: 10, color: 'var(--color-text-dim)' }}>→</span>}
      </div>
    </div>
  )
}
