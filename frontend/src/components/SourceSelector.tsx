import type { SourceBody, BackendType } from '../types'

interface Props {
  selected: SourceBody[]
  onChange: (bodies: SourceBody[]) => void
  backend: BackendType
  onBackendChange: (b: BackendType) => void
  onGenerate: () => void
  loading: boolean
}

const SOURCES: { id: SourceBody; label: string; sub: string }[] = [
  { id: 'EU_AI_Act', label: 'EU AI Act', sub: 'Art. 5, 14, 60' },
  { id: 'NASA_NPR', label: 'NASA NPR', sub: '8715.3E · 8705.4A' },
  { id: 'NASA_Lessons_Learned', label: 'NASA Lessons', sub: 'Historical corpus' },
]

export function SourceSelector({ selected, onChange, backend, onBackendChange, onGenerate, loading }: Props) {
  function toggle(id: SourceBody) {
    onChange(
      selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id],
    )
  }

  return (
    <div
      style={{
        padding: '16px 20px',
        borderBottom: '1px solid var(--color-border)',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        flexWrap: 'wrap',
      }}
    >
      {/* Source chips */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', flex: 1 }}>
        {SOURCES.map((s) => {
          const active = selected.includes(s.id)
          return (
            <button
              key={s.id}
              onClick={() => toggle(s.id)}
              data-active={active ? 'true' : 'false'}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                padding: '6px 12px',
                borderRadius: 8,
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 500,
                  color: active ? '#a78bfa' : 'var(--color-text-muted)',
                  pointerEvents: 'none',
                }}
              >
                {s.label}
              </span>
              <span style={{ fontSize: 10, color: 'var(--color-text-dim)', pointerEvents: 'none' }}>{s.sub}</span>
            </button>
          )
        })}
      </div>

      {/* Backend toggle */}
      <div
        style={{
          display: 'flex',
          gap: 0,
          borderRadius: 8,
          border: '1px solid var(--color-border)',
          overflow: 'hidden',
        }}
      >
        {(['mock', 'openai'] as BackendType[]).map((b) => (
          <button
            key={b}
            onClick={() => onBackendChange(b)}
            style={{
              padding: '6px 14px',
              fontSize: 11,
              fontWeight: 500,
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
              background: backend === b ? 'rgba(139,92,246,0.15)' : 'transparent',
              color: backend === b ? 'var(--color-accent)' : 'var(--color-text-dim)',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {b}
          </button>
        ))}
      </div>

      {/* Generate button */}
      <button
        onClick={onGenerate}
        disabled={loading}
        style={{
          padding: '8px 20px',
          borderRadius: 8,
          border: 'none',
          background: loading
            ? 'rgba(139,92,246,0.3)'
            : 'linear-gradient(135deg, #8b5cf6, #6366f1)',
          color: '#fff',
          fontSize: 13,
          fontWeight: 500,
          cursor: loading ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          transition: 'opacity 0.15s',
          opacity: loading ? 0.7 : 1,
          boxShadow: loading ? 'none' : '0 0 20px rgba(139,92,246,0.3)',
        }}
      >
        {loading ? (
          <>
            <Spinner />
            Generating…
          </>
        ) : (
          'Generate Report'
        )}
      </button>
    </div>
  )
}

function Spinner() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      style={{ animation: 'spin 0.8s linear infinite' }}
    >
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <circle cx="7" cy="7" r="5.5" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" />
      <path d="M7 1.5A5.5 5.5 0 0 1 12.5 7" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}
