# Phase 2 — Risultati verificati e limiti

Verifica: 27 novembre 2026. Nessun PDF o record reale incluso nella repository.

## Estrazione reale: ispezione tecnica limitata

| PDF comunale AICA | Righe estratte / dichiarate | Validazione strutturale | Revisione |
| --- | --- | --- | --- |
| Agrigento | 480 / 480 | 347 | 133 |
| Aragona | 5 / 5 | 3 | 2 |
| Ribera | 72 / 72 | 38 | 34 |
| Totale campioni | 557 / 557 | 388 | 169 |

I tre campioni sono PDF di interventi programmati con lo stesso layout a sei colonne.
Le 169 righe in revisione contengono il segnaposto 99999 nell'indirizzo: non è stato
sostituito o interpretato come un civico. Non sono emersi errori documentali nei tre
campioni; la concordanza del totale non prova ogni singolo campo né lo stato sul campo.
Le righe COMPLETATO rimangono lavori dichiarati completati, non ripristini idrici.
Le date di pubblicazione, programmazione e ripristino non sono disponibili nel layout
riconosciuto e rimangono null. I PDF non costituiscono fixture reali distribuite.

Hash, anomalie e metriche aggregate sono in `docs/reports/real-inspection-*.json`.
Il report Agrigento include completezza per campo: misurazione non null, non indice
di accuratezza. Copertura del solo campione: 1/43 comuni; non copertura del gestore.
Gli altri due report sono riepiloghi tecnici, non dataset di eventi.

## Scenario sintetico riproducibile

`uv run python scripts/demo_history.py --output data/demo-synthetic` produce:

- 5 documenti analizzati, con 8 righe osservate complessivamente.
- 6 osservazioni strutturalmente valide, 2 record in quarantena, 0 errori documentali.
- 2 interventi distinti validati nello storico, non 6 eventi distinti.
- Una sequenza con ripetizione, modifica, scomparsa, ricomparsa e dichiarazione esplicita
  di ripristino; nessuna data di ripristino imputata.

Il riepilogo e i report per run sono in `docs/reports/synthetic-quality.json` e vengono
rigenerati come artefatto della CI. Tutti gli interventi della demo sono fittizi.
Gli identificativi, gli indirizzi e gli stati sintetici non descrivono attività AICA.

## Verifiche software

Test unitari del parser geometrico, regressioni su underscore, indirizzi multilinea,
continuazioni di rete tra pagine, layout sconosciuti e totali discordanti. Test di
qualità su duplicati, codici mancanti, comuni sconosciuti, stati non riconosciuti,
date incoerenti, provenienza e campi incompleti. Test di integrazione dello storico,
rollback, replay idempotente, assenze conservative, conflitti tra documenti,
separazione real/synthetic, round-trip degli export e CLI locale.

La CI esegue Ruff lint/format, pytest, scenario sintetico, check e build web già presenti.
Il report non considera un test sintetico come verifica di copertura di tutti i layout
reali. Verifica locale finale: 39 test passati; Ruff lint e format superati; check Astro
senza diagnostiche; build statica riuscita. Build wheel riuscita con risorse ISTAT
incluse. PyMuPDF emette cinque DeprecationWarning SWIG, senza errori di test.
L'esito della CI remota viene riportato nella PR.

## Limiti

- Sono stati verificati tre campioni, non tutti i comuni o tutte le versioni storiche.
- Supportato il layout tabellare a sei colonne. PDF scannerizzati, altri layout,
  continuazioni ambigue e pagine non riconosciute richiedono revisione; nessun OCR.
- Non esiste ancora un parser di comunicati o turnazioni e non si fa entity matching
  tra prosa, avvisi e codici intervento.
- Gli stati ammessi aggiuntivi (IN CORSO, SOSPESO e FORNITURA RIPRISTINATA) sono gestiti
  e testati sinteticamente; non sono stati osservati nei tre campioni reali. Gli stati
  reali osservati sono PIANIFICATO, COMPLETATO e ANNULLATO.
- `validated` significa controlli strutturali superati, non validazione indipendente.
- Non ricostruiamo lo storico anteriore alle osservazioni effettive. Righe in revisione
  non aggiornano la proiezione corrente. Un documento con quarantena non prova assenze.
- Non esiste ancora una UI di revisione o una procedura di promozione delle correzioni:
  i record da revisionare restano separati e si correggono soltanto con nuova evidenza.
- Nessuna garanzia di frequenza AICA, stabilità del codice tra anni o completezza degli
  interventi rispetto ai lavori effettivi. Le variazioni descrivono la fonte osservata.
- Gli artefatti GitHub non sono storage durevole e possono scadere. Il workflow reale
  resta manuale e bloccato. Non è stato eseguito con acquisizioni reali.

## Attivazione e Phase 3

Servono verifica documentata di condizioni di acquisizione e riuso, attribuzione,
minimizzazione degli indirizzi, permesso di storage su GitHub, backup durevole e
riconciliazione dello storico precedente. Registro e variabili SOURCES_VERIFIED e
HISTORY_STORAGE_VERIFIED devono essere approvati; il cron resta commentato.

Per Phase 3: qualificare tutti i layout e la copertura gestore, definire il vocabolario
degli stati con la fonte, realizzare revisione tracciata, introdurre un archivio durevole,
aggiungere parser distinti per comunicati e turni, e solo poi progettare consultazione
e pubblicazione dei dataset autorizzati. Verificare ancora gli obblighi di licenza
PyMuPDF prima di distribuire servizi che lo incorporano.
