# Vinnioi

Osservatorio civico indipendente, open source e apartitico sull'acqua nella provincia
di Agrigento, ispirato a OpenDataSicilia. Sito previsto: https://vinnioi.it.
Non è un canale ufficiale dei gestori.

## Stato

Phase 3: connettori HTML AICA e Siciliacque, eventi fonte separati dalle osservazioni,
calendari di distribuzione, correlazioni candidate e revisione tracciata degli
interventi. DuckDB schema 3 migra in modo additivo lo storico Phase 2.

La validità dell'intervento è distinta dalla qualità dell'indirizzo: il civico
segnaposto 99999 resta nullo e la stringa originale è conservata. Nessun ripristino
è dedotto da completamento lavori, scomparsa di righe o previsioni.

**Acquisizione sistematica, workflow reale e pubblicazione sono disabilitati.**
Backup/restore locali sono verificati; nessuno storage esterno è attivato. Il workflow
reale non può usare artefatti temporanei come unico archivio. Il frontend non è una
dashboard: include soltanto un contratto JSON e una fixture sintetica aggiuntivi.

Vedere [risultati e limiti Phase 3](docs/phase3-verifica.md),
[revisione](docs/revisione.md), [storage](docs/storage.md) e
[licenze e sicurezza](docs/licenze-sicurezza.md). I risultati delle
[Phase 2](docs/phase2-verifica.md) restano documentati come verifica storica.

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

## Integrazione degli eventi e dei calendari

Demo completa offline con eventi fittizi di due fonti, variazione di calendario,
revisione, correlazione candidata e prova backup/restore:

```sh
uv run python scripts/demo_integration.py --output data/demo-integration
```

Usare una directory nuova. Per HTML già disponibili localmente, il manifest JSON
contiene `channel`, `path` e `source_url`; i canali ammessi sono
`aica_communications`, `siciliacque_notices`, `aica_turnations`.

```sh
uv run vinnioi-integrate ingest --manifest data/input/html-manifest.json \
  --synthetic --observed-at 2026-11-20T12:00:00+00:00 \
  --database data/synthetic/integration.duckdb --output data/synthetic/exports
uv run vinnioi-integrate preview --database data/synthetic/integration.duckdb \
  --output data/synthetic/frontend-preview.json
```

Per input reali omettere `--synthetic` e registrare il tempo effettivo di acquisizione;
non mescolare dati reali e fittizi. Le CLI restituiscono 2 per errori o dati da revisionare.
La revisione della quarantena richiede una decisione esplicita secondo lo schema
`docs/review-decision.schema.json`: non avviene automaticamente all'avvio.

La fixture `apps/web/fixtures/water-data.synthetic.json` e lo schema
`docs/frontend-water-data.schema.json` sono contratti per una futura interfaccia,
non un dataset reale pubblicato. Gli export completi possono contenere evidenze
locali da minimizzare e non devono essere copiati nella directory pubblica dell'app.

## Acquisizione reale

Tutti i canali reali sono bloccati dal registro delle fonti. Esempi intenzionalmente disabilitati:

```sh
uv run vinnioi-history --limit 1
uv run vinnioi-integrate ingest --channel siciliacque_notices \
  --database data/history/vinnioi.duckdb --output data/exports
```

La CLI documentale Phase 1 resta disponibile e usa lo stesso blocco del canale PDF:

```sh
uv run vinnioi --limit 1 --output data/staging
```

Prima di abilitare un canale seguire [la verifica delle fonti](docs/fonti.md), aggiornare
`config/sources.toml` in una PR e documentare le condizioni accettate. Le CLI applicano limiti
espliciti e controllano robots.txt a ogni run. Gli HTML hanno approvazioni separate
dai PDF. Non è stato riattivato il workflow reale.
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
