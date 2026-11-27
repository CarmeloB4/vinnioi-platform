import { z } from 'zod';
import { municipalities } from './model';
const code = z
  .string()
  .refine((v) => municipalities.some((m) => m.code === v), 'Comune ISTAT sconosciuto');
const source = z.enum(['aica', 'siciliacque']);
const sourceUrl = z
  .url()
  .refine(
    (v) =>
      ['www.aicaonline.it', 'www.siciliacque.it'].includes(new URL(v).hostname) &&
      new URL(v).protocol === 'https:' &&
      !new URL(v).username &&
      !new URL(v).password,
  );
const timestamp = z.iso.datetime({ offset: true });
const category = z.enum([
  'guasto',
  'interruzione',
  'manutenzione_programmata',
  'riduzione_portata',
  'emergenza_idrica',
  'potabilita',
  'ripristino_confermato',
]);
const event = z
  .object({
    event_id: z.string().regex(/^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$/),
    source_id: source,
    title: z.string(),
    categories: z.array(category).min(1),
    source_url: sourceUrl,
    published_on: z.iso.date().nullable(),
    acquired_at: timestamp,
    reliability: z.enum(['rule_based', 'needs_review', 'human_reviewed']),
    validation_status: z.enum(['validated', 'needs_review']),
    restoration_confirmed: z.boolean(),
    network_level: z.enum(['adduction', 'local_distribution', 'unspecified']),
    municipality_istat_codes: z.array(code),
    declared_status: z.string().nullable().optional(),
    restoration_expected_on: z.iso.date().nullable().optional(),
  })
  .refine(
    (e) =>
      new URL(e.source_url).hostname ===
      (e.source_id === 'aica' ? 'www.aicaonline.it' : 'www.siciliacque.it'),
    'URL non coerente con la fonte',
  )
  .refine(
    (e) => e.restoration_confirmed === e.categories.includes('ripristino_confermato'),
    'Categoria e conferma di ripristino incoerenti',
  );
const technical = z
  .object({
    intervention_id: z.string().regex(/^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$/),
    municipality: z.string().nullable(),
    municipality_istat_code: code.nullable(),
    intervention_type: z.string().nullable(),
    network_type: z.string().nullable(),
    reported_status: z.string().nullable(),
    address_quality: z.string().nullable(),
    source_url: sourceUrl,
    last_seen_at: timestamp,
  })
  .refine((t) => new URL(t.source_url).hostname === 'www.aicaonline.it', 'Fonte tecnica non AICA');
const turn = z
  .object({
    turnation_id: z.string(),
    municipality: z.string().nullable(),
    municipality_istat_code: code.nullable(),
    zone: z.string().nullable(),
    reservoir: z.string().nullable(),
    date: z.iso.date().nullable(),
    time_slot: z.string().nullable(),
    valid_from: z.iso.date().nullable(),
    valid_until: z.iso.date().nullable(),
    notes: z.string().nullable(),
    validation_status: z.enum(['validated', 'needs_review']),
    calendar_version: z.string(),
    source_url: sourceUrl,
    actual_delivery_confirmed: z.literal(false),
  })
  .refine(
    (t) => new URL(t.source_url).hostname === 'www.aicaonline.it',
    'Fonte turnazioni non AICA',
  );
export const datasetSchema = z.object({
  schema_version: z.literal(3),
  generated_at: timestamp,
  publication_approved: z.boolean(),
  data_origin: z.enum(['real', 'synthetic', 'empty']),
  recent_events: z.array(event),
  events_by_municipality: z.record(z.string(), z.array(z.string())),
  technical_interventions: z.array(technical),
  turnations: z.array(turn),
  timeline: z.array(
    z.object({
      entity_type: z.enum(['water_event', 'technical_intervention', 'turnation']),
      entity_id: z.string(),
      observed_at: timestamp,
      changes: z.array(z.string()),
      present_in_calendar: z.boolean().optional(),
    }),
  ),
  territorial_indicators: z.array(
    z.object({
      municipality_istat_code: code,
      municipality: z.string(),
      operator_coverage: z.string(),
      explicitly_mentioned_events: z.number(),
      service_status: z.literal('unknown'),
    }),
  ),
  last_update: z.object({
    last_attempt_at: timestamp.nullable(),
    last_success_at: timestamp.nullable(),
    last_source_observed_at: timestamp.nullable(),
    status: z.string(),
    errors: z.number(),
    review_records: z.number(),
    scheduled_acquisition_enabled: z.literal(false),
    caveat: z.string(),
  }),
});
export type Dataset = z.infer<typeof datasetSchema>;
export type WaterEvent = z.infer<typeof event>;
export type Technical = z.infer<typeof technical>;
