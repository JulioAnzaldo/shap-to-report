import type { EventMeta } from '../types'

interface Props {
  events: EventMeta[]
  selected: string | null
  onSelect: (id: string) => void
}

const archetypeColor: Record<string, string> = {
  concentrated: '#8b5cf6',
  mid: '#60a5fa',
  diffuse: '#34d399',
  conflicting: '#fbbf24',
  adversarial: '#f87171',
}

const archetypeLabel: Record<string, string> = {
  concentrated: 'CONC',
  mid: 'MID',
  diffuse: 'DIFF',
  conflicting: 'CONF',
  adversarial: 'ADV',
}

export function EventPicker({ events, selected, onSelect }: Props) {
  return (
    <aside
      style={{
        width: 220,
        flexShrink: 0,
        borderRight: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto',
        background: 'var(--color-surface)',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '20px 16px 12px',
          borderBottom: '1px solid var(--color-border)',
        }}
      >
        <div
          style={{
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: '0.1em',
            color: 'var(--color-text-muted)',
            textTransform: 'uppercase',
          }}
        >
          Events
        </div>
        <div style={{ fontSize: 11, color: 'var(--color-text-dim)', marginTop: 2 }}>
          {events.length} anomaly windows
        </div>
      </div>

      {/* List */}
      <div style={{ flex: 1, padding: '8px 0' }}>
        {events.map((ev) => {
          const isSelected = ev.event_id === selected
          const color = archetypeColor[ev.archetype] ?? '#6b6b7e'
          const label = archetypeLabel[ev.archetype] ?? ev.archetype.slice(0, 4).toUpperCase()
          const gini = ev.gini_coefficient != null ? ev.gini_coefficient.toFixed(2) : '—'

          return (
            <button
              key={ev.event_id}
              onClick={() => onSelect(ev.event_id)}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '8px 16px',
                background: isSelected ? 'rgba(139,92,246,0.1)' : 'transparent',
                border: 'none',
                borderLeft: isSelected ? '2px solid var(--color-accent)' : '2px solid transparent',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'background 0.15s',
              }}
              onMouseEnter={(e) => {
                if (!isSelected) (e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.03)'
              }}
              onMouseLeave={(e) => {
                if (!isSelected) (e.currentTarget as HTMLButtonElement).style.background = 'transparent'
              }}
            >
              {/* Archetype dot */}
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: color,
                  flexShrink: 0,
                }}
              />

              {/* Content */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: 12,
                    fontWeight: isSelected ? 500 : 400,
                    color: isSelected ? 'var(--color-text)' : 'var(--color-text-muted)',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  {ev.event_id}
                </div>
                <div
                  style={{
                    fontSize: 10,
                    color: 'var(--color-text-dim)',
                    marginTop: 1,
                    display: 'flex',
                    gap: 6,
                  }}
                >
                  <span style={{ color }}>{label}</span>
                  <span>G={gini}</span>
                  <span>{ev.subsystem}</span>
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </aside>
  )
}
