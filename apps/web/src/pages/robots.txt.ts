import { portal } from '../lib/adapter';
export function GET() {
  return new Response(
    portal.mode === 'demo'
      ? 'User-agent: *\nDisallow: /\n'
      : 'User-agent: *\nAllow: /\nSitemap: https://vinnioi.it/sitemap.xml\n',
    { headers: { 'Content-Type': 'text/plain' } },
  );
}
