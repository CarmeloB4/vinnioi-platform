import type { Dataset, WaterEvent } from './contract';
export type { Dataset, WaterEvent, Technical } from './contract';
import reference from '../data/municipalities.json';

export const slugify = (name: string) =>
  name
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
export const municipalities = reference.map((m) => ({
  ...m,
  code: m.municipality_istat_code,
  name: m.municipality,
  slug: slugify(m.municipality),
}));
export type Portal = { mode: 'demo' | 'production'; state: 'ready' | 'empty'; data: Dataset };
export const categoryNames: Record<string, string> = {
  guasto: 'Guasto',
  interruzione: 'Interruzione',
  manutenzione_programmata: 'Manutenzione programmata',
  riduzione_portata: 'Riduzione di portata',
  emergenza_idrica: 'Emergenza idrica',
  potabilita: 'Potabilità',
  ripristino_confermato: 'Ripristino confermato',
};
export const sourceNames: Record<string, string> = { aica: 'AICA', siciliacque: 'Siciliacque' };
export const formatDate = (value?: string | null, time = false) =>
  value
    ? new Intl.DateTimeFormat('it-IT', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
        timeZone: 'Europe/Rome',
        ...(time ? ({ hour: '2-digit', minute: '2-digit' } as const) : {}),
      }).format(new Date(value.length === 10 ? value + 'T12:00:00Z' : value))
    : 'Non disponibile';
export const eventStatus = (e: WaterEvent) =>
  e.restoration_confirmed
    ? 'Fornitura ripristinata, dichiarata'
    : e.restoration_expected_on
      ? 'Ripristino previsto'
      : e.declared_status || 'Stato non disponibile';
export function emptyData(): Dataset {
  return {
    schema_version: 3,
    generated_at: new Date().toISOString(),
    publication_approved: false,
    data_origin: 'empty',
    recent_events: [],
    events_by_municipality: {},
    technical_interventions: [],
    turnations: [],
    timeline: [],
    territorial_indicators: [],
    last_update: {
      last_attempt_at: null,
      last_success_at: null,
      last_source_observed_at: null,
      status: 'no_data',
      errors: 0,
      review_records: 0,
      scheduled_acquisition_enabled: false,
      caveat: 'L’assenza di dati non indica l’assenza di disservizi.',
    },
  };
}
export function filterEvents(
  events: WaterEvent[],
  filters: {
    municipality?: string;
    category?: string;
    status?: string;
    source?: string;
    from?: string;
    until?: string;
  },
) {
  return events.filter(
    (e) =>
      (!filters.municipality || e.municipality_istat_codes.includes(filters.municipality)) &&
      (!filters.category || e.categories.includes(filters.category as never)) &&
      (!filters.source || e.source_id === filters.source) &&
      (!filters.status || eventStatus(e) === filters.status) &&
      (!filters.from || (!!e.published_on && e.published_on >= filters.from)) &&
      (!filters.until || (!!e.published_on && e.published_on <= filters.until)),
  );
}
