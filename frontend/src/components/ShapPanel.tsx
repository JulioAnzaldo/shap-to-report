import type { EventMeta } from '../types'

interface Props {
  event: EventMeta
}

const FEATURE_DESC: Record<string, string> = {
  mean:  'Average telemetry value over the window — deviation indicates sustained bias or drift',
  std:   'Standard deviation — elevated values indicate increased variability or noise',
  min:   'Minimum value in window — low outliers may indicate dropouts or clipping',
  max:   'Maximum value in window — high outliers may indicate spikes or saturation',
  slope: 'Linear trend over window — non-zero slope indicates a directional drift',
}

interface SubsystemInfo {
  label: string
  fullName: string
  color: string
  description: string
  failureModes: string[]
}

const SUBSYSTEM_INFO: Record<string, SubsystemInfo> = {
  P: {
    label: 'Power',
    fullName: 'Power Subsystem (P-channels)',
    color: '#fcd34d',
    description:
      'Manages electrical power generation, storage, and distribution across the spacecraft. On SMAP, this includes solar array output, battery charge/discharge cycles, and power bus regulation. Anomalies in power channels can affect all other subsystems and are among the highest-priority faults.',
    failureModes: [
      'Solar array output degradation or shadowing',
      'Battery cell imbalance or capacity loss',
      'Power bus voltage excursion outside nominal range',
      'Unexpected load switching causing transient spikes',
      'Regulator fault causing sustained over/under-voltage',
    ],
  },
  R: {
    label: 'Radiation',
    fullName: 'Radiation / RF Subsystem (R-channels)',
    color: '#7dd3fc',
    description:
      'Covers radio frequency communications and radiation environment monitoring. Includes uplink/downlink signal levels, bit error rates, and radiation dose accumulation. Contextual anomalies in R-channels often correlate with passage through the South Atlantic Anomaly (SAA) or solar energetic particle events.',
    failureModes: [
      'Single-event upsets (SEUs) from radiation exposure',
      'Transponder lock loss during high-radiation passes',
      'Antenna pointing error reducing link margin',
      'Bit error rate increase during solar particle events',
    ],
  },
  T: {
    label: 'Thermal',
    fullName: 'Thermal Control Subsystem (T-channels)',
    color: '#f97316',
    description:
      'Maintains spacecraft components within operational temperature limits using heaters, radiators, and thermal blankets. SMAP operates in a sun-synchronous orbit; thermal anomalies often correlate with eclipse entry/exit transitions or heater control failures.',
    failureModes: [
      'Heater failure causing component temperature drop below survival limit',
      'Radiator blockage or degradation causing overheating',
      'Thermal cycling fatigue on connectors or solder joints',
      'Eclipse transition causing rapid temperature swing',
      'Thermostat failure causing uncontrolled heating',
    ],
  },
  A: {
    label: 'Attitude',
    fullName: 'Attitude Control Subsystem (A-channels)',
    color: '#a78bfa',
    description:
      'Controls spacecraft orientation using reaction wheels, magnetorquers, and star trackers. SMAP requires precise attitude control to maintain its 6-day repeat ground track and L-band radar pointing. Attitude anomalies can cause science data gaps or, in severe cases, loss of power positive orientation.',
    failureModes: [
      'Reaction wheel speed exceedance or bearing degradation',
      'Star tracker blinding from bright objects (Moon, Sun)',
      'Magnetorquer saturation during high-latitude passes',
      'Attitude determination error from sensor noise',
      'Safe mode entry due to attitude error threshold breach',
    ],
  },
  D: {
    label: 'Data / Downlink',
    fullName: 'Data Handling / Downlink (D-channels)',
    color: '#4ade80',
    description:
      'Manages onboard data storage, processing, and transmission to ground stations. Includes solid-state recorder (SSR) health, data compression, and downlink scheduling. Point anomalies in D-channels often indicate memory errors or data pipeline faults.',
    failureModes: [
      'Solid-state recorder bit errors or sector failures',
      'Data pipeline overflow causing dropped science packets',
      'Downlink scheduling conflict causing data loss',
      'Onboard processor fault or watchdog reset',
      'Memory scrubbing failure allowing error accumulation',
    ],
  },
  E: {
    label: 'Electrical',
    fullName: 'Electrical / Electronics (E-channels)',
    color: '#60a5fa',
    description:
      'Covers general electrical subsystems including power conditioning electronics, relay states, and electrical interface health. E-channel anomalies often reflect component aging, connector degradation, or electromagnetic interference.',
    failureModes: [
      'Relay contact resistance increase causing voltage drop',
      'Capacitor degradation affecting power conditioning',
      'Electromagnetic interference from other subsystems',
      'Connector pin corrosion or fretting',
      'Component aging causing parameter drift',
    ],
  },
  F: {
    label: 'Fault / Flag',
    fullName: 'Fault Detection / Flag Channels (F-channels)',
    color: '#f87171',
    description:
      'Represents fault detection and isolation (FDIR) flag channels that indicate the spacecraft\'s onboard fault management state. Anomalies in F-channels may indicate that the spacecraft\'s own fault detection system has triggered, or that a flag is being set/cleared unexpectedly.',
    failureModes: [
      'Spurious fault flag triggering unnecessary safe mode',
      'FDIR threshold misconfiguration causing false positives',
      'Fault flag not clearing after anomaly resolution',
      'Cascading fault flags from a single root cause',
    ],
  },
  G: {
    label: 'Guidance',
    fullName: 'Guidance / Navigation (G-channels)',
    color: '#34d399',
    description:
      'Covers guidance, navigation, and control (GNC) sensor outputs including GPS receiver data, inertial measurement unit (IMU) readings, and orbit determination parameters. G-channel anomalies can affect orbit maintenance maneuvers and science data geolocation accuracy.',
    failureModes: [
      'GPS receiver signal loss during orbital maneuvers',
      'IMU drift causing navigation error accumulation',
      'Orbit determination solution divergence',
      'Thruster performance degradation affecting delta-V accuracy',
    ],
  },
}

export function ShapPanel({ event }: Props) {
  const attr = event.attribution
  if (!attr) return null

  const names = attr.feature_names
  const values = attr.feature_attributions
  const maxAbs = Math.max(...values.map(Math.abs), 0.001)

  // Sort by absolute value descending
  const sorted = names
    .map((name, i) => ({ name, value: values[i] }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))

  return (
    <div
      style={{
        borderRadius: 10,
        border: '1px solid var(--color-border)',
        background: 'var(--color-surface-2)',
        overflow: 'hidden',
        marginBottom: 16,
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '8px 14px',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span
          style={{
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: 'var(--color-text-dim)',
          }}
        >
          SHAP Attribution — {attr.channel_id}
        </span>
        <span
          style={{
            fontSize: 10,
            fontFamily: 'var(--font-mono)',
            color: 'var(--color-text-dim)',
          }}
        >
          Gini = {attr.attribution_concentration.toFixed(3)}
        </span>
      </div>

      {/* Bars */}
      <div style={{ padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {sorted.map(({ name, value }) => {
          const pct = (Math.abs(value) / maxAbs) * 100
          const isPositive = value >= 0
          const barColor = isPositive ? '#8b5cf6' : '#f87171'
          const isTop = name === sorted[0].name

          return (
            <div key={name} title={FEATURE_DESC[name] ?? name}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  marginBottom: 3,
                }}
              >
                <span
                  style={{
                    width: 44,
                    fontSize: 11,
                    fontFamily: 'var(--font-mono)',
                    color: isTop ? 'var(--color-text)' : 'var(--color-text-muted)',
                    fontWeight: isTop ? 600 : 400,
                    flexShrink: 0,
                  }}
                >
                  {name}
                </span>

                {/* Bar track */}
                <div
                  style={{
                    flex: 1,
                    height: 6,
                    borderRadius: 3,
                    background: 'var(--color-border)',
                    overflow: 'hidden',
                    position: 'relative',
                  }}
                >
                  <div
                    style={{
                      position: 'absolute',
                      left: 0,
                      top: 0,
                      height: '100%',
                      width: `${pct}%`,
                      background: barColor,
                      borderRadius: 3,
                      opacity: isTop ? 1 : 0.55,
                      transition: 'width 0.5s ease',
                    }}
                  />
                </div>

                <span
                  style={{
                    width: 48,
                    fontSize: 10,
                    fontFamily: 'var(--font-mono)',
                    color: barColor,
                    textAlign: 'right',
                    flexShrink: 0,
                  }}
                >
                  {value >= 0 ? '+' : ''}{value.toFixed(3)}
                </span>
              </div>

              {/* Feature description — only show for top feature */}
              {isTop && (
                <div
                  style={{
                    marginLeft: 52,
                    fontSize: 10,
                    color: 'var(--color-text-dim)',
                    lineHeight: 1.4,
                    marginBottom: 2,
                  }}
                >
                  {FEATURE_DESC[name] ?? ''}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Window info */}
      <div
        style={{
          padding: '8px 14px',
          borderTop: '1px solid var(--color-border)',
          display: 'flex',
          gap: 20,
        }}
      >
        {event.window_start_index != null && (
          <StatPill label="Window start" value={`idx ${event.window_start_index}`} />
        )}
        {event.window_size != null && (
          <StatPill label="Window size" value={`${event.window_size} samples`} />
        )}
        {event.ensemble_score != null && (
          <StatPill label="Ensemble score" value={event.ensemble_score.toFixed(3)} />
        )}
        {event.ensemble_agreement != null && event.n_models_in_ensemble != null && (
          <StatPill
            label="Agreement"
            value={`${event.ensemble_agreement}/${event.n_models_in_ensemble} models`}
          />
        )}
      </div>
    </div>
  )
}

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 9, color: 'var(--color-text-dim)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
        {label}
      </div>
      <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)', marginTop: 1 }}>
        {value}
      </div>
    </div>
  )
}

export function ChannelAttributionPanel({ event }: Props) {
  const chanId = event.subsystem  // e.g. "D-2", "A-9", "P-1"
  const prefix = chanId?.[0]?.toUpperCase() ?? '?'
  const info = SUBSYSTEM_INFO[prefix]
  const anomalyClass = (event as any).anomaly_class as string | undefined

  if (!info) return null

  const anomalyClassInfo = anomalyClass === 'point'
    ? { label: 'Point anomaly', color: '#f87171', desc: 'An isolated spike or dropout — typically a transient fault, bit flip, or sensor glitch. Usually short-duration.' }
    : anomalyClass === 'contextual'
    ? { label: 'Contextual anomaly', color: '#fcd34d', desc: 'A value normal in isolation but anomalous given surrounding context — e.g., a reading normal at one mission phase but not another.' }
    : null

  return (
    <div style={{
      borderRadius: 10,
      border: '1px solid var(--color-border)',
      background: 'var(--color-surface-2)',
      overflow: 'hidden',
      marginBottom: 16,
    }}>
      <div style={{
        padding: '8px 14px',
        borderBottom: '1px solid var(--color-border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-text-dim)' }}>
          Subsystem Context — {chanId}
        </span>
        <span style={{
          fontSize: 10, padding: '2px 8px', borderRadius: 4,
          background: `${info.color}18`, border: `1px solid ${info.color}35`,
          color: info.color, fontWeight: 600,
        }}>
          {info.label}
        </span>
      </div>

      <div style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {/* Subsystem description */}
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 4 }}>
            {info.fullName}
          </div>
          <div style={{ fontSize: 12, color: 'var(--color-text)', lineHeight: 1.65 }}>
            {info.description}
          </div>
        </div>

        {/* Typical failure modes */}
        <div style={{
          padding: '10px 12px', borderRadius: 8,
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid var(--color-border)',
        }}>
          <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-text-dim)', marginBottom: 6 }}>
            Typical failure modes
          </div>
          <ul style={{ margin: 0, paddingLeft: 16, display: 'flex', flexDirection: 'column', gap: 3 }}>
            {info.failureModes.map((m, i) => (
              <li key={i} style={{ fontSize: 12, color: 'var(--color-text-muted)', lineHeight: 1.5 }}>{m}</li>
            ))}
          </ul>
        </div>

        {/* Anomaly class context */}
        {anomalyClassInfo && (
          <div style={{
            padding: '8px 12px', borderRadius: 8,
            background: `${anomalyClassInfo.color}08`,
            border: `1px solid ${anomalyClassInfo.color}25`,
            display: 'flex', gap: 10, alignItems: 'flex-start',
          }}>
            <span style={{ color: anomalyClassInfo.color, fontSize: 14, flexShrink: 0, marginTop: 1 }}>◈</span>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: anomalyClassInfo.color, marginBottom: 3 }}>
                {anomalyClassInfo.label}
              </div>
              <div style={{ fontSize: 12, color: 'var(--color-text-muted)', lineHeight: 1.55 }}>
                {anomalyClassInfo.desc}
              </div>
            </div>
          </div>
        )}

        {/* Labeled window info */}
        {(event as any).labeled_anomaly_start != null && (
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            <StatPill label="Anomaly onset" value={`idx ${(event as any).labeled_anomaly_start}`} />
            <StatPill label="Anomaly end" value={`idx ${(event as any).labeled_anomaly_end}`} />
            <StatPill label="Duration" value={`${(event as any).labeled_anomaly_end - (event as any).labeled_anomaly_start} samples`} />
          </div>
        )}

        <div style={{ fontSize: 10, color: 'var(--color-text-dim)', lineHeight: 1.5 }}>
          Channel IDs are anonymized (Hundman et al., KDD 2018). Subsystem type inferred from channel prefix.
          GDN/TrAD (CPSC 491) will provide inter-sensor attribution once integrated.
        </div>
      </div>
    </div>
  )
}
