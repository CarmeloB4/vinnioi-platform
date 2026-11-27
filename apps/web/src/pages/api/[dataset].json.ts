import { portal } from '../../lib/adapter';
import { municipalities } from '../../lib/model';
import type { APIRoute } from 'astro';
export function getStaticPaths() {
  return [
    {
      params: { dataset: 'municipalities' },
      props: {
        value: {
          source: 'ISTAT',
          license: 'CC BY 4.0',
          attribution: 'Fonte ISTAT, selezione provincia di Agrigento; elaborazione Vinnioi',
          data: municipalities.map(({ code, name }) => ({
            municipality_istat_code: code,
            municipality: name,
          })),
        },
      },
    },
    ...(portal.mode === 'demo'
      ? [
          {
            params: { dataset: 'demo-events' },
            props: {
              value: {
                data_origin: 'synthetic',
                notice: 'Eventi fittizi, non descrivono disservizi reali',
                data: portal.data.recent_events,
              },
            },
          },
        ]
      : []),
    ...(portal.mode === 'production' && portal.state === 'ready'
      ? [
          {
            params: { dataset: 'water-events' },
            props: { value: { data_origin: 'real', data: portal.data.recent_events } },
          },
        ]
      : []),
  ];
}
export const GET: APIRoute = ({ props }) =>
  new Response(JSON.stringify(props.value, null, 2) + '\n', {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
