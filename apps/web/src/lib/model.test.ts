import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { adapt, loadPortal } from './adapter';
import { municipalities, filterEvents, eventStatus, slugify } from './model';
import { datasetSchema } from './contract';
const raw = JSON.parse(readFileSync('fixtures/portal.synthetic.json', 'utf8'));
const fixture = datasetSchema.parse(raw);
test('43 comuni ufficiali con codici e slug unici', () => {
  assert.equal(municipalities.length, 43);
  assert.equal(new Set(municipalities.map((m) => m.slug)).size, 43);
  assert.equal(slugify('Canicattì'), 'canicatti');
  assert.equal(slugify('Sant’Angelo Muxaro'), 'sant-angelo-muxaro');
});
test('filtri combinati, fonte, categoria, stato e date editoriali', () => {
  assert.equal(
    filterEvents(fixture.recent_events, {
      municipality: '084041',
      source: 'aica',
      category: 'manutenzione_programmata',
      from: '2026-11-20',
      until: '2026-11-20',
    }).length,
    1,
  );
  assert.equal(filterEvents(fixture.recent_events, { municipality: '084011' }).length, 0);
  assert.equal(filterEvents(fixture.recent_events, { status: 'Ripristino previsto' }).length, 1);
});
test('previsioni distinte dalle dichiarazioni di ripristino', () => {
  assert.match(
    eventStatus(fixture.recent_events.find((e) => e.restoration_confirmed)!),
    /dichiarata/,
  );
  assert.equal(
    eventStatus(fixture.recent_events.find((e) => e.restoration_expected_on)!),
    'Ripristino previsto',
  );
});
test('produzione vuota senza fallback alla demo', () => {
  const portal = loadPortal({});
  assert.equal(portal.mode, 'production');
  assert.equal(portal.state, 'empty');
  assert.equal(portal.data.recent_events.length, 0);
  assert.equal(portal.data.last_update.last_source_observed_at, null);
});
test('fixture sintetiche rifiutate in produzione anche con flag alterato', () => {
  assert.throws(() => adapt(raw, 'production'));
  assert.throws(() => adapt({ ...raw, publication_approved: true }, 'production'));
});
test('modalità e destinazione demo esplicite', () => {
  assert.equal(adapt(raw, 'demo').mode, 'demo');
  assert.throws(() => adapt(raw, 'unknown'));
  assert.throws(() => loadPortal({ VINNIOI_MODE: 'demo', VINNIOI_DEPLOYMENT: 'production' }));
  assert.throws(() => loadPortal({ VINNIOI_MODE: 'demo', CF_PAGES_BRANCH: 'main' }));
});
test('produzione richiede autorizzazione legata ai byte e per fonte', () => {
  const data = { ...raw, data_origin: 'real', publication_approved: true };
  const bytes = JSON.stringify(data);
  const approval = {
    approved: true,
    dataset_sha256: createHash('sha256').update(bytes).digest('hex'),
    approved_by: 'revisore-test',
    approved_at: '2026-11-27T12:00:00Z',
    source_permissions: {
      aica: { redistribution_approved: true, license_url: 'https://example.org/license' },
      siciliacque: { redistribution_approved: true, license_url: 'https://example.org/license' },
    },
  };
  assert.equal(adapt(data, 'production', approval, bytes).mode, 'production');
  assert.throws(() =>
    adapt(data, 'production', { ...approval, dataset_sha256: 'a'.repeat(64) }, bytes),
  );
  assert.throws(() => adapt(data, 'production', { ...approval, source_permissions: {} }, bytes));
});
test('contratti scartano date incomplete e impediscono record non validati in produzione', () => {
  const demo = structuredClone(raw);
  demo.turnations[0].date = null;
  assert.equal(adapt(demo, 'demo').data.turnations.length, raw.turnations.length - 1);
  const invalid = structuredClone(raw);
  invalid.recent_events[0].municipality_istat_codes = ['999999'];
  assert.throws(() => adapt(invalid, 'demo'));
});
test('identificativi sicuri nei permalink', () => {
  const invalid = structuredClone(raw);
  invalid.recent_events[0].event_id = '../outside';
  assert.throws(() => adapt(invalid, 'demo'));
});
test('confini reali: 43 geometrie e isole comprese, senza punti di intervento', () => {
  const geo = JSON.parse(readFileSync('public/data/municipalities.geojson', 'utf8'));
  assert.equal(geo.features.length, 43);
  assert.deepEqual(
    new Set(geo.features.map((f: any) => f.properties.code)),
    new Set(municipalities.map((m) => m.code)),
  );
  assert.ok(geo.features.every((f: any) => ['Polygon', 'MultiPolygon'].includes(f.geometry.type)));
});

test('provenienza, ripristini e permalink coerenti', () => {
  const wrongSource = structuredClone(raw);
  wrongSource.recent_events[0].source_url = 'https://www.siciliacque.it/avviso/';
  assert.throws(() => adapt(wrongSource, 'demo'));
  const wrongStatus = structuredClone(raw);
  wrongStatus.recent_events[0].restoration_confirmed =
    !wrongStatus.recent_events[0].restoration_confirmed;
  assert.throws(() => adapt(wrongStatus, 'demo'));
  const duplicate = structuredClone(raw);
  duplicate.recent_events.push(duplicate.recent_events[0]);
  assert.throws(() => adapt(duplicate, 'demo'));
});
