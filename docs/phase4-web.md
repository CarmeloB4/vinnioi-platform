# Phase 4 — Portale, utilizzo e verifica

Il portale è pronto per revisione in PR, senza deploy o modifiche ad account e DNS.
La pipeline Python, il registro delle fonti e `update-data.yml` rimangono invariati:
l'acquisizione reale è disabilitata. Le autorizzazioni operative e lo storage durevole
non sono stati risolti da questa fase.

## Percorsi e interfaccia

- `/`: presentazione, ricerca comunale, indicatori, aggiornamenti e anteprima dei confini.
- `/dashboard/`: filtri combinabili per comune, categoria, stato dichiarato, fonte e date
  editoriali. Grafici testuali temporali, territoriali e per categoria; lavori tecnici
  in registro separato, consultabili anche nelle pagine comunali.
- `/comuni/` e 43 `/comuni/[slug]/`: ricerca anche senza accenti, osservazioni, lavori,
  timeline, turnazioni validate e datate, fonti e copertura esplicitamente sconosciuta.
- `/eventi/[id]/`, `/interventi/[id]/`: dettagli minimizzati, provenienza e timestamp.
  “COMPLETATO” riguarda un lavoro; un termine previsto non conferma il ripristino.
- `/mappa/`: MapLibre su richiesta, poligoni ufficiali, selezione, popup, aggregati,
  legenda e collegamenti. Elenco HTML equivalente sempre disponibile, comprese le isole.
- `/opendata/`, `/fonti/`, `/metodologia/`, `/chi-siamo/`, `/accessibilita/`, pagina 404.

Inter locale, palette richiesta, tipografia e layout responsive. Lo slot `data-logo-slot`
contiene per ora il nome testuale, da sostituire con il logo ufficiale fornito dal progetto.
Nessun logo ridisegnato. L'assenza di dati non appare come indicatore positivo. I conteggi
si riferiscono al dataset e non alle utenze, alla copertura dei gestori o a eventi unici.

## Avvio locale

Requisiti: Node >=22.23.4, npm; Python 3.12 e uv per la pipeline.

```sh
npm ci
npm run dev                   # produzione vuota, nessuna fixture
npm run dev:demo              # demo esplicitamente sintetica
npm run build                 # apps/web/dist
npm run build:demo            # apps/web/dist-demo
npm run preview -w apps/web   # anteprima produzione
npm run preview:demo -w apps/web
```

Astro può avviare preview in background negli ambienti agent: usare `-- --ignore-lock`
se occorre un processo in foreground. Playwright gestisce automaticamente i due server
4173 (demo) e 4174 (produzione) e li arresta alla fine.

## Adapter e input di produzione

Variabili di build:

| Variabile | Effetto |
| --- | --- |
| `VINNIOI_MODE` | `production` predefinito, oppure `demo` esplicito |
| `VINNIOI_DEPLOYMENT` | `production` vieta la demo, anche nelle preview configurate così |
| `CF_PAGES_BRANCH` | `main` vieta la demo; impostata da Cloudflare Pages |
| `VINNIOI_DATA_PATH` | Percorso assoluto dell'input JSON reale revisionato; assente = produzione vuota |
| `VINNIOI_AUTHORIZATION_PATH` | Percorso assoluto del manifest di approvazione separato |
| `VINNIOI_OUT_DIR` | Solo sviluppo/test: separa dist e dist-demo |

L'input deve rispettare schema 3 (`src/lib/contract.ts`), dichiarare `data_origin=real`
e `publication_approved=true`. Eventi validati, nessun `needs_review`, turnazioni con
data completa e report senza errori o record da revisionare. Permalink duplicati,
URL non coerenti con l'ente o categorie di ripristino contraddittorie bloccano la build.
Il contratto tecnico Phase 3 espone solo la proiezione validata; la sua provenienza
e revisione restano responsabilità del processo di approvazione, non dedotte dall'UI.

Il manifest deve contenere `approved: true`, `dataset_sha256` (SHA-256 degli esatti
byte UTF-8 del JSON), `approved_by`, `approved_at` (ISO con timezone), e
`source_permissions` con una voce per ogni fonte presente, ciascuna con
`redistribution_approved: true` e `license_url`. È un'attestazione manuale verificabile
rispetto al file, non una firma crittografica del revisore. Non basta cambiare i flag
della fixture e non esiste un'approvazione reale inclusa nel repository.

Input e manifest devono stare fuori da `apps/web/public` e `apps/web/fixtures`, anche
tramite symlink. Non versionare documenti, database, evidenze o dati personali. Gli
export integrali locali non sono l'input pubblico. La pipeline continua a esportare
`publication_approved=false`: per abilitare pubblicazioni future occorre una PR che
definisca minimizzazione, verifiche delle licenze e processo di approvazione reale.

Senza input si generano 52 pagine HTML di produzione, senza percorsi evento/demo.
La demo genera 59 pagine HTML con fixture fittizie, banner globale, robots disallow
e meta noindex. I download demo non vengono generati nella produzione vuota.
I metadati territoriali ISTAT restano scaricabili in entrambe le modalità.

## Provenienza dei confini e download

Fonte primaria: [confini amministrativi ISTAT](https://www.istat.it/notizia/confini-delle-unita-amministrative-a-fini-statistici-al-1-gennaio-2018-2/),
[archivio generalizzato 2026](https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati/2026/Limiti01012026_g.zip),
[note legali CC BY 4.0](https://www.istat.it/note-legali/).

`public/data/municipalities.provenance.json` conserva URL, data di riferimento,
attribuzione, hash dell'archivio originale e hash del GeoJSON. I confini sono ai soli
fini statistici. Trasformazione riproducibile da archivio già scaricato localmente:

```sh
uv run scripts/prepare_boundaries.py --archive /percorso/Limiti01012026_g.zip
```

Lo script isolato PEP 723 usa pyshp/pyproj bloccati, seleziona i codici 084, verifica
43 geometrie, riproietta dal CRS dichiarato e arrotonda a 5 decimali. Non cambia
le dipendenze o l'acquisizione della pipeline. L'anagrafica deriva dal CSV ISTAT
versionato in `packages/ingestion/src/vinnioi/resources/`; la sua provenienza resta lì.
I soli download attuali sono anagrafica, confini/provenienza e, solo in demo, eventi
sintetici. Gli eventi reali avrebbero un endpoint solo dopo i gate sopra descritti.
CSV/Parquet operativi rimangono export locali. MIT invariata; Inter è OFL e MapLibre
BSD-3-Clause, con le rispettive licenze nei pacchetti npm. Nessun documento operativo
AICA/Siciliacque è incluso nel sito.

## Cloudflare Pages: configurazione proposta, non attivata

[Guida ufficiale Astro](https://developers.cloudflare.com/pages/framework-guides/deploy-an-astro-site/).
Collegare la repository solo dopo autorizzazione alla pubblicazione. Root repository,
build command `npm ci && npm run build`, output `apps/web/dist`, Node >=22.23.4
(`.node-version`). Output statico, nessun adapter SSR, Worker o servizio a pagamento.

Produzione: branch main, `VINNIOI_MODE=production`, `VINNIOI_DEPLOYMENT=production`.
Lasciare assenti i percorsi input finché licenze e workflow di approvazione non siano
verificati. Non usare artefatti Actions temporanei come unico storage. Non inserire
input operativi in variabili pubbliche o directory servite.

Preview: branch di PR, produzione vuota consigliata. Una preview dimostrativa richiede
scelta esplicita di demo e destinazione non production; rimangono banner e noindex.
Noindex non è controllo d'accesso: non caricare contenuti riservati. I canonical puntano
a `https://vinnioi.it`; prima del lancio verificare redirect e indicizzazione.

DNS, solo in una successiva operazione autorizzata: aggiungere `vinnioi.it` nella
sezione Custom domains di Pages e seguire i record richiesti dal pannello Cloudflare.
Per apex verificare prima delega/nameserver e record esistenti; non sostituire record
MX/TXT o altri servizi. Un eventuale `www` richiede dominio/record dedicato e redirect
verso il canonical scelto. Non sono stati letti o modificati account o record DNS.

HTTPS: Pages emette il certificato per il dominio verificato; attendere lo stato
attivo e controllare HTTP→HTTPS, certificato e assenza di mixed content prima del lancio.
Rollback: dalla lista deploy promuovere l'ultima build di produzione verificata oppure
fare revert del commit e ricostruire. Conservare identificativo deploy/commit e manifest
della pubblicazione. Un rollback del sito non modifica lo storico DuckDB. Non usare
il cambio DNS come normale rollback del codice.

## Verifiche

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
npm run check
npm run test:web
npm exec -w apps/web -- playwright install chromium
npm run test:e2e
```

La CI esegue gli stessi controlli; su Ubuntu installa anche le dipendenze di Chromium.
Playwright costruisce entrambe le modalità. Risultati finali della fase:
90 test Python, 11 test unitari frontend e 8 test Chromium; Astro check senza errori
o warning. Ruff e formattazione Python passano. Le build sono statiche e non richiedono
accesso alle fonti operative. I warning SWIG/PyMuPDF preesistenti non invalidano i test.

I test coprono 43 route, filtri combinati, stato vuoto, gate di autorizzazione e hash,
provenienza, previsioni/ripristini, mappa caricabile, errore geometrie con alternativa,
navigazione mobile, skip link e overflow orizzontale. axe-core controlla le regole
WCAG 2.2 AA applicabili su sette percorsi principali. Non è una certificazione di
conformità: restano da completare prove con screen reader, browser/Safari/Firefox,
zoom e utenti reali. JavaScript disabilitato conserva contenuti e percorsi comunali;
filtri e grafici interattivi richiedono JS e lo dichiarano. MapLibre (~1,1 MB non gzip)
è un chunk separato caricato soltanto all'attivazione; non usa tile o geocoding esterni.
Nessuna immagine remota o analytics; font locali. Misurazione Lighthouse da eseguire
su una preview autorizzata, senza attribuire punteggi non misurati.

Screenshot verificati localmente e rigenerabili dal test browser:

| Modalità | Desktop 1440 px | Mobile 390 px |
| --- | --- | --- |
| Demo | [Screenshot](screenshots/phase4-demo-desktop.png) | [Screenshot](screenshots/phase4-demo-mobile.png) |
| Produzione vuota | [Screenshot](screenshots/phase4-production-desktop.png) | [Screenshot](screenshots/phase4-production-mobile.png) |

## Raccomandazioni Phase 5

1. Verificare licenze per fonte/canale e minimizzazione; definire revisione e manifest
   di pubblicazione, con audit e responsabilità, prima di rendere reali gli input web.
2. Integrare storage durevole, backup/restore e retention verificati prima di riattivare
   acquisizioni periodiche. Conservare separati dati reali, demo e quarantena.
3. Formalizzare nel contratto della pipeline stato dichiarato e termini previsti quando
   presenti nella fonte; nessuna inferenza automatica da completamento lavori.
4. Verificare accessibilità con tecnologie assistive, performance e resa dei confini
   su dispositivi modesti. Sostituire lo slot con il logo ufficiale quando fornito.
5. Approvare una preview e il piano DNS/HTTPS/rollback prima di un lancio pubblico.
