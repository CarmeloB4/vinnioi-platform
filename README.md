# Vinnioi

Osservatorio civico indipendente, open source e apartitico sull'acqua nella provincia
di Agrigento, ispirato a OpenDataSicilia. Sito previsto: https://vinnioi.it.
Non è un canale ufficiale dei gestori.

## Stato

Phase 2: estrazione geometrica delle righe PDF AICA, normalizzazione ISTAT,
storico incrementale DuckDB e snapshot CSV/JSON/Parquet. Eventi e osservazioni
rimangono distinti; record dubbi in quarantena. Nessun ripristino dedotto dalla
scomparsa di una riga o dal completamento di un lavoro.

Acquisizione sistematica e pubblicazione **disabilitate**. La repository contiene
soltanto fixture sintetiche generate in codice, l'anagrafica amministrativa ISTAT
(CC BY 4.0 con attribuzione) e report tecnici aggregati. Frontend invariato.
Vedere [risultati e limiti della Phase 2](docs/phase2-verifica.md).

## Avvio

Requisiti: Python 3.12, [uv](https://docs.astral.sh/uv/), Node 22.23.4+ e npm.

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

## Storico e riproduzione offline

```sh
uv run python scripts/demo_history.py --output data/demo-synthetic
```

Genera cinque snapshot sintetici e dimostra novità, ripetizioni, variazioni,
assenze, ricomparse, dichiarazione esplicita di ripristino e quarantena. Usare
una directory nuova: il comando non cancella database esistenti. I comuni citati
sono reali, ma tutti gli interventi della demo sono fittizi.

Per PDF già disponibili localmente usare un manifest JSON (non versionare documenti
reali senza permesso). Esempio di struttura, non un campione reale:

```json
[{"path":"synthetic.pdf","municipality":"Agrigento","source_url":"https://www.aicaonline.it/interventi_programmati/interventi_agrigento.pdf"}]
```

```sh
uv run vinnioi-history --manifest data/input/manifest.json --synthetic \
  --observed-at 2026-01-01T12:00:00+00:00 --run-id demo-1 \
  --database data/synthetic/history.duckdb --output data/synthetic/exports
```

`--synthetic` serve solo per fixture. Per documenti reali ometterlo e fornire il
momento effettivo dell'osservazione, senza retrodatare il download. Database reali e
sintetici non possono essere mescolati. `--run-id` rende idempotente un replay identico;
un run diverso deve avere un timestamp successivo. I backfill usano un database separato.

Lo snapshot corrente è indicato dal file `LATEST` nella directory degli export.
La CLI restituisce exit code 2 se ci sono errori documentali o record da revisionare:
lo storico e i report vengono comunque salvati, con i dati dubbi separati.

```sh
uv run vinnioi-history --database data/history/vinnioi.duckdb --export-only
```

## Acquisizione reale

Entrambe le CLI sono bloccate intenzionalmente dal registro delle fonti:

```sh
uv run vinnioi-history --limit 1
```

La CLI documentale Phase 1 resta disponibile:

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
- `tests`: test unitari, di integrazione e regressione con PDF sintetici.
- `scripts/demo_history.py`: scenario riproducibile offline e report di qualità.
- `config`: registro delle fonti e blocco dell'acquisizione.
- `docs`: fonti, modello, architettura e decisioni.

## Cloudflare Pages

Build dalla radice: `npm ci && npm run build`; directory di output:
`apps/web/dist`; Node 22.23.4+. Nessun adapter SSR necessario: output statico.
Nessun deploy o servizio a pagamento è stato attivato. Vedere la
[guida ufficiale](https://developers.cloudflare.com/pages/framework-guides/deploy-an-astro-site/).

## Licenze

Il codice del progetto mantiene la [licenza MIT esistente](LICENSE), invariata.
La MIT non si estende ai contenuti delle fonti o alle dipendenze.
L’anagrafica deriva da ISTAT, CC BY 4.0: attribuzione e hash in
`packages/ingestion/src/vinnioi/resources/municipalities.provenance.json`. I documenti di terzi
non sono distribuiti. PyMuPDF ha condizioni AGPL/commerciali: prima di distribuire una
soluzione che lo incorpora o di esporre servizi basati su di esso, verificare gli
obblighi applicabili (vedere docs/architettura.md). Nessuna licenza commerciale è
stata acquistata. Le fixture sono sintetiche.
