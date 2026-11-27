import { createHash } from 'node:crypto';
import { readFileSync, realpathSync } from 'node:fs';
import { resolve, relative } from 'node:path';
import { z } from 'zod';
import { emptyData, type Portal } from './model';
import { datasetSchema } from './contract';

export function adapt(
  raw: unknown,
  mode: string,
  authorization?: unknown,
  originalBytes?: string,
): Portal {
  if (mode !== 'demo' && mode !== 'production')
    throw new Error('VINNIOI_MODE deve essere demo o production');
  const data = datasetSchema.parse(raw);
  for (const ids of [
    data.recent_events.map((e) => e.event_id),
    data.technical_interventions.map((t) => t.intervention_id),
  ]) {
    if (new Set(ids).size !== ids.length) throw new Error('Permalink duplicati nel dataset');
  }
  if (mode === 'demo') {
    if (data.data_origin !== 'synthetic' || data.publication_approved)
      throw new Error('La demo accetta solo fixture sintetiche');
  } else {
    if (data.data_origin !== 'real' || data.publication_approved !== true)
      throw new Error('Produzione: dati reali autorizzati obbligatori');
    const approval = z
      .object({
        approved: z.literal(true),
        dataset_sha256: z.string().regex(/^[a-f0-9]{64}$/),
        approved_by: z.string().min(1),
        approved_at: z.iso.datetime({ offset: true }),
        source_permissions: z.record(
          z.string(),
          z.object({ redistribution_approved: z.literal(true), license_url: z.url() }),
        ),
      })
      .parse(authorization);
    if (
      !originalBytes ||
      createHash('sha256').update(originalBytes).digest('hex') !== approval.dataset_sha256
    )
      throw new Error('Hash autorizzazione non corrispondente');
    const sources = new Set([
      ...data.recent_events.map((e) => e.source_id),
      ...(data.technical_interventions.length || data.turnations.length ? ['aica'] : []),
    ]);
    for (const source of sources)
      if (!approval.source_permissions[source]) throw new Error('Permesso della fonte mancante');
    if (
      data.recent_events.some(
        (e) => e.validation_status !== 'validated' || e.reliability === 'needs_review',
      ) ||
      data.turnations.some((t) => t.validation_status !== 'validated' || !t.date)
    )
      throw new Error('Produzione: record non validati');
    if (data.last_update.errors || data.last_update.review_records)
      throw new Error('Produzione: report di qualità non approvato');
  }
  // Celle senza date complete non sono mai mostrate come turni operativi, neppure in demo.
  data.turnations = data.turnations.filter(
    (t) => t.validation_status === 'validated' && t.date !== null,
  );
  return {
    mode,
    state:
      data.recent_events.length || data.technical_interventions.length || data.turnations.length
        ? 'ready'
        : 'empty',
    data,
  };
}
export function loadPortal(env: NodeJS.ProcessEnv = process.env): Portal {
  const mode = env.VINNIOI_MODE || 'production';
  if (
    mode === 'demo' &&
    (env.VINNIOI_DEPLOYMENT === 'production' || env.CF_PAGES_BRANCH === 'main')
  )
    throw new Error('Demo vietata sulla destinazione di produzione');
  if (mode === 'demo')
    return adapt(
      JSON.parse(readFileSync(`${process.cwd()}/fixtures/portal.synthetic.json`, 'utf8')),
      mode,
    );
  if (mode !== 'production') throw new Error('Modalità non riconosciuta');
  if (!env.VINNIOI_DATA_PATH) return { mode, state: 'empty', data: emptyData() };
  if (!env.VINNIOI_AUTHORIZATION_PATH) throw new Error('Autorizzazione di pubblicazione mancante');
  for (const file of [env.VINNIOI_DATA_PATH, env.VINNIOI_AUTHORIZATION_PATH]) {
    const location = realpathSync(file);
    for (const folder of ['public', 'fixtures']) {
      const rel = relative(resolve(process.cwd(), folder), location);
      if (rel === '' || (!rel.startsWith('..') && !rel.startsWith('/')))
        throw new Error('Input di produzione in directory pubblica o fixture');
    }
  }
  const bytes = readFileSync(env.VINNIOI_DATA_PATH, 'utf8');
  return adapt(
    JSON.parse(bytes),
    mode,
    JSON.parse(readFileSync(env.VINNIOI_AUTHORIZATION_PATH, 'utf8')),
    bytes,
  );
}
export const portal = loadPortal();
