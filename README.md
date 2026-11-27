# Vinnioi

Osservatorio civico indipendente, open source e apartitico sull'acqua nella provincia
di Agrigento, ispirato a OpenDataSicilia. Sito previsto: https://vinnioi.it.
Non è un canale ufficiale dei gestori.

## Stato

Prima base tecnica: scoperta dei PDF AICA degli interventi programmati, estrazione
testuale e dataset di **documenti da revisionare**, non di singoli lavori validati.
Nessun dato reale incluso, nessuna pubblicazione o aggiornamento periodico attivato.
Guasti, turnazioni, risorse e ripristini richiedono adattatori e validazione dedicati.

## Avvio

Requisiti: Python 3.12, [uv](https://docs.astral.sh/uv/), Node 22.23.4+.23.4+ e npm.

```sh
uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .
npm ci
npm run check
npm run build
npm run dev
```

La pipeline è bloccata intenzionalmente dal registro delle fonti:

```sh
uv run vinnioi --limit 1 --output data/staging
```

Prima di abilitarla seguire [la verifica delle fonti](docs/fonti.md), aggiornare
`config/sources.toml` in una PR e documentare le condizioni accettate. La CLI limita
l'acquisizione a un PDF per impostazione predefinita e controlla robots.txt a ogni run.
CSV, JSON, Parquet e DuckDB sono risultati locali ignorati da Git. Non includono il
PDF né il testo integrale estratto. Non sono automaticamente pubblicabili.

## Struttura

- `packages/ingestion/src/vinnioi`: schema, scoperta AICA, HTTP, parser PDF, export, CLI.
- `apps/web`: Astro statico, TypeScript strict e Tailwind 4.
- `tests`: test offline con contenuti sintetici.
- `config`: registro delle fonti e blocco dell'acquisizione.
- `docs`: fonti, modello, architettura e decisioni.

## Cloudflare Pages

Build dalla radice: `npm ci && npm run build`; directory di output:
`apps/web/dist`; Node 22.23.4+. Nessun adapter SSR necessario: output statico.
Nessun deploy o servizio a pagamento è stato attivato. Vedere la
[guida ufficiale](https://developers.cloudflare.com/pages/framework-guides/deploy-an-astro-site/).

## Licenze

Il codice del progetto mantiene la [licenza MIT esistente](LICENSE), invariata.
La MIT non si estende ai contenuti delle fonti o alle dipendenze. I documenti di terzi
non sono distribuiti. PyMuPDF ha condizioni AGPL/commerciali: prima di distribuire una
soluzione che lo incorpora o di esporre servizi basati su di esso, verificare gli
obblighi applicabili (vedere docs/architettura.md). Nessuna licenza commerciale è
stata acquistata. Le fixture sono sintetiche.
