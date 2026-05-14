import { useState, useEffect, useRef } from 'react'
import { fetchEvents, fetchReport } from './api'
import { EventPicker } from './components/EventPicker'
import { SourceSelector } from './components/SourceSelector'
import { ReportPanel } from './components/ReportPanel'
import { RefusalCard } from './components/RefusalCard'
import { ShapPanel, ChannelAttributionPanel } from './components/ShapPanel'
import { GlossaryPanel } from './components/GlossaryPanel'
import type { EventMeta, SituationalReport, SourceBody, BackendType, ProvenanceEntry } from './types'

const STATUS_STEPS = [
  'Loading event data…',
  'Retrieving regulatory context…',
  'Retrieving historical precedents…',
  'Composing prompt…',
  'Generating report…',
  'Validating output…',
]

export default function App() {
  const [events, setEvents] = useState<EventMeta[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [sources, setSources] = useState<SourceBody[]>(['EU_AI_Act', 'NASA_NPR', 'NASA_Lessons_Learned'])
  const [backend, setBackend] = useState<BackendType>('openai')
  const [report, setReport] = useState<SituationalReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [statusStep, setStatusStep] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [eventsError, setEventsError] = useState<string | null>(null)
  const [activeChunk, setActiveChunk] = useState<ProvenanceEntry | null>(null)
  const [fromCache, setFromCache] = useState(false)
  const statusTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    fetchEvents()
      .then(setEvents)
      .catch((e) => setEventsError(e.message))
  }, [])

  function startStatusCycle() {
    setStatusStep(0)
    let step = 0
    statusTimer.current = setInterval(() => {
      step = Math.min(step + 1, STATUS_STEPS.length - 1)
      setStatusStep(step)
    }, 900)
  }

  function stopStatusCycle() {
    if (statusTimer.current) {
      clearInterval(statusTimer.current)
      statusTimer.current = null
    }
  }

  async function handleGenerate(forceRefresh = false) {
    if (!selectedId) return
    setLoading(true)
    setError(null)
    setReport(null)
    setFromCache(false)
    startStatusCycle()
    try {
      const { report: r, cached: wasCached } = await fetchReport(selectedId, sources, backend, forceRefresh)
      setFromCache(wasCached)
      setReport(r)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      stopStatusCycle()
      setLoading(false)
    }
  }

  const selectedEvent = events.find((e) => e.event_id === selectedId)

  return (
    <div style={{ display: 'flex', height: '100vh', background: 'var(--color-bg)', overflow: 'hidden', position: 'relative' }}>
      {/* Background glow */}
      <div style={{
        position: 'fixed', top: -200, left: '30%',
        width: 600, height: 600, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(139,92,246,0.06) 0%, transparent 70%)',
        pointerEvents: 'none', zIndex: 0,
      }} />

      {/* Sidebar */}
      {eventsError ? (
        <div style={{
          width: 220, flexShrink: 0, display: 'flex', alignItems: 'center',
          justifyContent: 'center', padding: 16,
          borderRight: '1px solid var(--color-border)',
          fontSize: 12, color: '#f87171', textAlign: 'center',
        }}>
          Backend offline.<br />Start uvicorn first.
        </div>
      ) : (
        <EventPicker events={events} selected={selectedId} onSelect={(id) => { setSelectedId(id); setReport(null); setError(null) }} />
      )}

      {/* Main */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative', zIndex: 1 }}>

        {/* Top bar */}
        <header style={{
          padding: '0 24px', height: 52,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-surface)', flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 22, height: 22, borderRadius: 6,
              background: 'linear-gradient(135deg, #8b5cf6, #6366f1)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, fontWeight: 700, color: '#fff',
            }}>S</div>
            <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--color-text)', letterSpacing: '-0.01em' }}>
              shap-to-report
            </span>
            <span style={{ fontSize: 10, color: 'var(--color-text-dim)', padding: '2px 6px', borderRadius: 4, border: '1px solid var(--color-border)' }}>
              v0.1
            </span>
          </div>

          {selectedEvent && (
            <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
              <MetaItem label="Mission" value={selectedEvent.mission} />
              <MetaItem label="Channel" value={selectedEvent.subsystem} />
              <MetaItem label="Archetype" value={selectedEvent.archetype} />
              {selectedEvent.gini_coefficient != null && (
                <MetaItem label="Gini" value={selectedEvent.gini_coefficient.toFixed(3)} mono />
              )}
            </div>
          )}
        </header>

        {/* Source selector */}
        <SourceSelector
          selected={sources}
          onChange={setSources}
          backend={backend}
          onBackendChange={setBackend}
          onGenerate={() => handleGenerate(false)}
          loading={loading}
        />

        {/* Main content area */}
        <main style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>

          {/* Empty state */}
          {!selectedId && !loading && !report && <EmptyState />}

          {/* Selected, not yet generated */}
          {selectedId && !loading && !report && !error && (
            <div style={{ maxWidth: 720, margin: '0 auto' }}>
              {selectedEvent && <ShapPanel event={selectedEvent} />}
              {selectedEvent && <ChannelAttributionPanel event={selectedEvent} />}
              <ReadyPrompt />
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60%', gap: 20 }}>
              <LoadingOrb />
              <StatusStepper steps={STATUS_STEPS} current={statusStep} />
            </div>
          )}

          {/* Error */}
          {error && (
            <div style={{
              margin: '32px auto', maxWidth: 480,
              padding: '16px 20px', borderRadius: 10,
              background: 'rgba(248,113,113,0.08)',
              border: '1px solid rgba(248,113,113,0.2)',
              fontSize: 13, color: '#fca5a5',
            }}>
              <strong style={{ display: 'block', marginBottom: 4 }}>Error</strong>
              {error}
            </div>
          )}

          {/* Report */}
          {report && !loading && (
            <div style={{ maxWidth: 720, margin: '0 auto' }}>
              {/* SHAP panel always shown above report */}
              {selectedEvent && <ShapPanel event={selectedEvent} />}
              {selectedEvent && <ChannelAttributionPanel event={selectedEvent} />}

              <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>
                  {report.event_id}
                </span>
                {report.degraded_mode !== 'none' && (
                  <span style={{
                    fontSize: 10, padding: '2px 8px', borderRadius: 4,
                    background: 'rgba(251,191,36,0.1)',
                    border: '1px solid rgba(251,191,36,0.2)',
                    color: '#fbbf24',
                  }}>DEGRADED</span>
                )}
                {fromCache && (
                  <span style={{
                    fontSize: 10, padding: '2px 8px', borderRadius: 4,
                    background: 'rgba(74,222,128,0.08)',
                    border: '1px solid rgba(74,222,128,0.2)',
                    color: '#4ade80',
                  }}>⚡ cached</span>
                )}
                <button
                  onClick={() => handleGenerate(true)}
                  title="Force regenerate (bypass cache)"
                  style={{
                    marginLeft: 'auto',
                    background: 'none',
                    border: '1px solid var(--color-border)',
                    borderRadius: 6,
                    padding: '3px 10px',
                    fontSize: 11,
                    color: 'var(--color-text-dim)',
                    cursor: 'pointer',
                  }}
                >
                  ↺ Regenerate
                </button>
              </div>

              {report.degraded_mode !== 'none'
                ? <RefusalCard report={report} />
                : <ReportPanel report={report} onChunkSelect={setActiveChunk} />
              }
            </div>
          )}
        </main>
      </div>

      {/* Glossary + chunk viewer — right panel */}
      <GlossaryPanel
        activeChunk={activeChunk}
        onClose={() => setActiveChunk(null)}
      />
    </div>
  )
}

function StatusStepper({ steps, current }: { steps: string[]; current: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'center' }}>
      {steps.map((step, i) => {
        const done = i < current
        const active = i === current
        return (
          <div
            key={step}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              opacity: done ? 0.35 : active ? 1 : 0.2,
              transition: 'opacity 0.3s',
            }}
          >
            <span style={{
              width: 16, height: 16, borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 9,
              background: done ? 'rgba(52,211,153,0.2)' : active ? 'rgba(139,92,246,0.2)' : 'transparent',
              border: done ? '1px solid rgba(52,211,153,0.4)' : active ? '1px solid rgba(139,92,246,0.4)' : '1px solid var(--color-border)',
              color: done ? '#34d399' : active ? '#8b5cf6' : 'var(--color-text-dim)',
            }}>
              {done ? '✓' : active ? '·' : '○'}
            </span>
            <span style={{
              fontSize: 12,
              color: active ? 'var(--color-text)' : 'var(--color-text-muted)',
              fontWeight: active ? 500 : 400,
            }}>
              {step}
            </span>
          </div>
        )
      })}
    </div>
  )
}

function MetaItem({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
      <span style={{ fontSize: 9, color: 'var(--color-text-dim)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
        {label}
      </span>
      <span style={{ fontSize: 11, color: 'var(--color-text-muted)', fontFamily: mono ? 'var(--font-mono)' : undefined }}>
        {value}
      </span>
    </div>
  )
}

function ReadyPrompt() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, padding: '24px 0', color: 'var(--color-text-dim)' }}>
      <div style={{ fontSize: 11 }}>Select source bodies above and click Generate Report</div>
    </div>
  )
}

function EmptyState() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '70%', gap: 16, textAlign: 'center' }}>
      <div style={{
        width: 64, height: 64, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(139,92,246,0.15), transparent)',
        border: '1px solid rgba(139,92,246,0.2)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 24, color: 'rgba(139,92,246,0.6)',
      }}>◎</div>
      <div>
        <div style={{ fontSize: 15, fontWeight: 500, color: 'var(--color-text-muted)', marginBottom: 6 }}>
          Select an anomaly event
        </div>
        <div style={{ fontSize: 12, color: 'var(--color-text-dim)', maxWidth: 280 }}>
          Choose an event from the sidebar, select regulatory source bodies, and generate a grounded situational report.
        </div>
      </div>
    </div>
  )
}

function LoadingOrb() {
  return (
    <div style={{
      width: 48, height: 48, borderRadius: '50%',
      border: '1.5px solid rgba(139,92,246,0.3)',
      borderTopColor: '#8b5cf6',
      animation: 'spin 1s linear infinite',
    }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
