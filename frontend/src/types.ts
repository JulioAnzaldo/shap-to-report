export interface ProvenanceEntry {
  source_body: string
  document: string
  section: string
  relevance_score: number
  text?: string
}

export type DegradedMode =
  | 'none'
  | 'shap_unavailable'
  | 'llm_unavailable'
  | 'insufficient_context_retrieval'
  | 'validation_failed'
  | 'model_low_confidence'

export type AnomalyType =
  | 'sensor_fault'
  | 'actuator_fault'
  | 'thermal_anomaly'
  | 'power_anomaly'
  | 'communication_anomaly'
  | 'attitude_anomaly'
  | 'propulsion_anomaly'
  | 'unknown'

export type SeverityLevel = 'low' | 'medium' | 'high' | 'critical'

export interface SituationalReport {
  event_id: string
  degraded_mode: DegradedMode
  anomaly_type?: AnomalyType
  severity?: SeverityLevel
  primary_features?: string[]
  explanation?: string
  confidence?: number
  ensemble_agreement_ratio?: number
  attribution_concentration?: number
  historical_precedent?: string
  provenance?: ProvenanceEntry[]
  operator_assessment?: string
  operator_decision?: string
  refusal_reason?: string
}

export interface AttributionData {
  channel_id: string
  feature_names: string[]
  feature_attributions: number[]
  attribution_concentration: number
}

export interface ChannelAttribution {
  method: string
  description: string
  values: number[]
  top_channels: { channel_index: number; attribution: number }[]
}

export interface EventMeta {
  event_id: string
  archetype: string
  mission: string
  subsystem: string
  gini_coefficient?: number
  ensemble_agreement?: number
  ensemble_score?: number
  n_models_in_ensemble?: number
  window_start_index?: number
  window_size?: number
  attribution?: AttributionData
  channel_attributions?: ChannelAttribution
  ground_truth_anomaly_type?: string
  ground_truth_severity?: string
}

export type SourceBody = 'EU_AI_Act' | 'NASA_NPR' | 'NASA_Lessons_Learned'

export type BackendType = 'mock' | 'openai'
