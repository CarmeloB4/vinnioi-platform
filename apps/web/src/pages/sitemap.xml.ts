import { municipalities } from '../lib/model';
import { portal } from '../lib/adapter';
export function GET() {
  const paths = [
    '/',
    '/dashboard/',
    '/mappa/',
    '/comuni/',
    '/opendata/',
    '/fonti/',
    '/metodologia/',
    '/chi-siamo/',
    '/accessibilita/',
    ...municipalities.map((m) => `/comuni/${m.slug}/`),
    ...portal.data.recent_events.map((e) => `/eventi/${e.event_id}/`),
    ...portal.data.technical_interventions.map((i) => `/interventi/${i.intervention_id}/`),
  ];
  return new Response(
    `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${paths.map((p) => `<url><loc>https://vinnioi.it${p}</loc></url>`).join('')}</urlset>`,
    { headers: { 'Content-Type': 'application/xml' } },
  );
}
