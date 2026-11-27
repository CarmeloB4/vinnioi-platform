# Phase 3 — Verifiche effettive e limiti

Data: 27 novembre 2026. Report aggregato: `docs/reports/phase3-real-qualification.json`.
Nessun articolo, PDF, indirizzo reale o dataset di eventi reali è distribuito nella PR.

## Risultati per fonte

| Fonte e verifica | Risultato effettivo | Limite |
| --- | --- | --- |
| Indice comunicazioni AICA | 10 collegamenti riconosciuti sulla prima pagina; un articolo operativo campione classificato come interruzione con Agrigento esplicitamente citato. | Nessuna scansione completa dell'archivio. Il ritorno alla normalità previsto per il giorno successivo non è conferma di ripristino. |
| Indice avvisi Siciliacque | 12 collegamenti riconosciuti; un avviso campione classificato guasto/interruzione, rete di adduzione e Licata esplicitamente citata. | Aragona nel nome dell'acquedotto non diventa comune colpito. Il termine previsto di riattivazione non conferma il ripristino. |
| PDF AICA Licata extra urbana | 3 righe su 3 dichiarate; layout verificato visivamente e variante del titolo qualificata per URL/comune corrispondenti. | Tre civici non disponibili, originali conservati. Nessuna data del lavoro dedotta dalla generazione del PDF. |
| PDF AICA Sciacca | 214 righe su 214 dichiarate, nessun errore documentale; 36 civici non disponibili e 178 indirizzi as_reported. | La validazione è strutturale, non una verifica sul campo. Non verificati tutti i PDF/versioni AICA. |
| Calendario AICA HTML | 3.807 celle estratte, comprese celle vuote, per 33 codici comunali riconosciuti. | Zero date complete nella struttura osservata; tutte le celle richiedono revisione. 11 collisioni di slot, 68 valori non riconosciuti, 32 celle con località incompleta, 64 con blocco sovracomunale non riconducibile a un comune. |

Le collisioni del calendario non sono eliminate silenziosamente: le righe conservano
posizione originale e identità distinta di revisione. Le sottozone AGRIGENTO – nome
quartiere mantengono il comune esplicito e il quartiere separato. Il blocco UTENZE
VOLTANO non viene assegnato automaticamente a un comune. I valori di nota ambigui
sono conservati senza interpretarli come erogazione avvenuta.

Robots AICA e Siciliacque hanno risposto 200 e sono stati registrati con hash.
Le regole osservate non sostituiscono la verifica dei termini di acquisizione e riuso.
I connettori reali restano bloccati dal registro; le letture svolte sono ispezioni
limitate autorizzate dal compito, non esecuzioni periodiche.

## Copertura territoriale

L'anagrafica amministrativa rimane di 43 comuni. L'indice interventi mostra 29 comuni
unici e il calendario 33 comuni riconosciuti. La pagina istituzionale
[L'Azienda](https://www.aicaonline.it/lazienda/) elenca i comuni fondatori: quel ruolo
non prova una copertura attuale completa. Le discrepanze tra elenchi, documenti e
sottozone impediscono di certificare un perimetro contrattuale attuale dai soli
campioni consultati. `operator_coverage` resta unknown.

`coverage_evidence` e `operator_coverage_evidence` registrano natura della prova,
URL, hash e data di controllo, distinguendo presenza di un PDF o blocco calendario
da copertura effettiva. Non si completano comuni mancanti né si deduce assenza del
servizio. Per gli eventi campione è verificata solo la citazione territoriale esplicita.

## Scenario sintetico e qualità

`scripts/demo_integration.py` crea due eventi fonte distinti, tre osservazioni di
evento, due slot di calendario e quattro osservazioni di turnazione. Una correlazione
resta candidate e una revisione esplicita promuove un intervento sintetico correggendo
lo stato con evidenza della fixture. Il backup locale è ripristinato e i conteggi
confrontati. Report: `docs/reports/phase3-synthetic-quality.json`.

La fixture frontend è `apps/web/fixtures/water-data.synthetic.json`, con provenienza
synthetic, publication_approved=false, timeline e indicatori territoriali senza stato
del servizio inventato. Non è collegata a una dashboard o a un deploy.

La suite comprende le regressioni precedenti e test su categorie, negazioni,
potabilità, previsioni, date relative, condotte omonime, calendari incompleti,
duplicati, migrazione, revisione, correlazioni, CLI, allowlist, robots e backup/restore.
Verifica locale: 90 test passati, Ruff lint/format superati, check Astro senza
diagnostiche e build statica riuscita. L’esito della CI remota viene riportato nella PR.
I test non certificano
copertura generale del linguaggio naturale o di tutti i layout reali.

## Limitazioni esplicite

- Un articolo corrisponde inizialmente a un evento fonte. Articoli con più episodi,
  date o aree richiedono revisione; non c'è segmentazione generale degli episodi.
- La classificazione deterministica è prudente ma non interpreta tutte le varianti
  linguistiche. Negazioni complesse possono causare omissioni conservative.
- I comuni citati in liste complesse possono essere conservati come mentioned_only,
  senza impatto attribuito automaticamente. Le abbreviazioni non sono completate.
- Le date complete restano date, gli orari restano stringhe dichiarate; non si
  fabbricano timestamp di inizio/fine combinando riferimenti ambigui.
- Il calendario reale osservato non permette una ricostruzione affidabile di mese e
  anno: non è dichiarato operativo come agenda con date complete.
- Le modifiche dei calendari con date complete sono testate sinteticamente; per i
  calendari ambigui è conservato lo storico per hash, senza unire slot di mesi diversi.
- La revisione tracciata implementata riguarda gli interventi in quarantena, non
  una UI o un workflow di approvazione degli eventi narrativi e delle turnazioni.
- Le correlazioni non sono validazioni di identità, non fondono fonti e non trasferiscono
  ripristini. Non sono stati prodotti legami reali confermati tra i campioni.
- Storage e restore sono locali. R2/S3/Releases sono opzioni documentate, senza adapter
  remoto operativo. Il workflow reale è esplicitamente bloccato finché non lo integra.
- Non è qualificata la redistribuzione dei contenuti AICA/Siciliacque. Restano necessari
  verifica del riuso, attribuzione e controllo di minimizzazione prima di pubblicare.

## Raccomandazioni Phase 4

Qualificare il perimetro contrattuale corrente e un insieme autorizzato di campioni;
concordare il vocabolario operativo e ottenere date complete dei calendari. Integrare
storage durevole con budget approvato e prove di restore fuori sede, completare la
revisione tracciata di eventi e calendari e valutare un adapter PDF permissivo con
parità verificata. Solo dopo progettare dashboard e pubblicazione dei dataset
minimizzati e autorizzati, mantenendo sempre visibili limiti, fonte e data dell'osservazione.
