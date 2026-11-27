# Istruzioni per gli agenti

Scrivere documentazione e messaggi del prodotto in italiano. Il progetto è civico,
indipendente e apartitico. Mantenere la licenza MIT esistente.

## Priorità

1. Provenienza, qualità, verificabilità dei dati.
2. Acquisizione rispettosa delle fonti e tracciamento delle incertezze.
3. Interfaccia accessibile, leggera e senza dati inventati.

## Regole sui dati

- Non inventare eventi o timestamp di pubblicazione. Usare null se sconosciuti.
- Distinguere guasti, attività programmate, turnazioni e ripristini dichiarati.
- Un termine previsto non conferma un ripristino. Un PDF aggiornato non è un nuovo guasto.
- Non dedurre stato del servizio da assenza di avvisi o da lavori eseguiti.
- Non salvare documenti di terzi, dati personali o testo integrale nel repository.
- La raggiungibilità e robots.txt non costituiscono una licenza di riuso.
- Non attivare schedule o pubblicazione senza verifica documentata delle fonti.
- Non aggiungere servizi a pagamento. Decisioni reversibili in docs/adr/.

## Verifica

Python 3.12 e uv; dipendenze bloccate in uv.lock. Dopo modifiche Python eseguire
`uv run ruff check .`, `uv run ruff format --check .` e `uv run pytest`.
Dopo modifiche web eseguire `npm run check`, `npm run test:web`, `npm run build`
e `npm run test:e2e` (Chromium Playwright installato).
I test devono restare offline, usare fixture sintetiche e coprire errori di formato,
provenienza, regole di classificazione e blocchi di acquisizione.

## Phase 2: storico e parser

- La chiave interna combina ente, codice ISTAT e codice dell'intervento della fonte.
- Non confondere `source_id` (ente) con `source_intervention_id` (codice AICA).
- Interventi: proiezione corrente dei record strutturalmente validati. Osservazioni:
  storico immutabile di quanto visto in un documento a una determinata acquisizione.
- `COMPLETATO` riguarda il lavoro, non la disponibilità dell'acqua. Solo lo stato
  esplicito `FORNITURA RIPRISTINATA` è riconosciuto come conferma; non assegnare
  `resolved_at` al momento del download se la data della fonte non è disponibile.
- Non riconciliare assenze su documenti incompleti, layout sconosciuti o con quarantena.
- Righe con identificativi duplicati, stati nuovi, comuni incerti
  o provenienza incoerente devono rimanere in revisione.
- I 43 comuni ISTAT rappresentano la copertura amministrativa. La presenza di un PDF
  non certifica la copertura del gestore; `operator_coverage` resta unknown.
- Non mescolare database sintetici e reali. Non sovrascrivere o cancellare uno storico.
- Dopo modifiche allo storico eseguire anche la demo sintetica in una directory nuova.
- Gli export locali non sono una pubblicazione. L'artefatto CI ordinario contiene solo
  il report sintetico. Qualsiasi storage di dati reali richiede condizioni verificate.

## Phase 3: eventi, calendari e continuità

- Il segnaposto civico finale 99999 segue la regola verificata AICA-99999-v1:
  address_original invariato, address senza quel suffisso, house_number=null e
  qualità distinta dalla validità dell'intervento. Non promuovere vecchie quarantene
  senza decisione esplicita, hash, fonte, motivazione e regola.
- Titolo e testo operativo dell'articolo sono separati da menu, contatti e footer.
  Negazioni e previsioni non confermano un ripristino. La potabilità è una categoria
  di dichiarazione della fonte, non un giudizio sanitario del progetto.
- Il nome di una condotta non attribuisce automaticamente impatto ai comuni omonimi.
  Distinguere area di servizio esplicita e sola menzione; il livello rete richiede evidenza.
- Date relative richiedono un ancoraggio editoriale; non completare un calendario
  usando mese o anno del download. Una cella programmata non prova erogazione.
- Eventi di fonti diverse restano distinti. Le correlazioni hanno motivazioni,
  versioni documentali e stato candidate: mai fusione o propagazione automatica.
- Schema 3 migra da 2 senza cancellare storico e quarantena. Fare backup prima di
  usare la migrazione su dati reali. Le decisioni di revisione sono append-only nell'API.
- Non riattivare update-data.yml finché storage durevole e licenze non sono verificati
  e integrati. Gli artefatti temporanei non possono essere l'unico storico.
- Contratti frontend: publication_approved=false e fixture soltanto sintetiche.
  Non copiare database, evidenze o indirizzi tecnici nelle directory pubbliche.
- Dopo modifiche Phase 3 eseguire anche scripts/demo_integration.py in directory nuova;
  comprende backup e restore locali verificati.

## Phase 4: portale pubblico

- Produzione è la modalità predefinita; senza input autorizzati mostra uno stato vuoto.
- Demo soltanto esplicita, con banner globale e noindex; mai su main o destinazione production.
- Non promuovere la fixture modificando flag. I dati reali richiedono revisione, permessi
  per fonte e manifest separato legato all'hash dei byte; vedere docs/phase4-web.md.
- Non copiare input operativi, manifest, database o indirizzi nelle directory pubbliche.
- Le geometrie comunali derivano da ISTAT CC BY 4.0, con provenienza e hash versionati.
  Non inventare coordinate degli eventi né dedurre copertura o stato del servizio dalla mappa.
- Mantenere i 43 percorsi comunali anche quando non esistono osservazioni pubblicabili.
- Il logo ufficiale resta uno slot: non ridisegnarlo. Nessuna pubblicazione o modifica DNS
  è autorizzata dalla sola preparazione della configurazione Cloudflare Pages.
- Screenshot e test browser usano fixture sintetiche oppure produzione vuota, mai dati reali.
