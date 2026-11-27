# Architettura

Monorepo con un package Python installabile e un'app Astro indipendente. Nessun
backend pubblico, database remoto o servizio a pagamento. Il checkout iniziale
conteneva solamente LICENSE MIT e .gitignore (commit f08b712).

## Flusso

Registro approvato → controllo robots → indice AICA → collegamenti ammessi →
PDF in memoria → testo per pagina → record documentale da revisionare → export locale.
La pubblicazione è un passaggio futuro separato: non esiste un percorso automatico
tra staging e frontend. L'interfaccia mostra uno stato vuoto esplicito.

HTTPX usa timeout, limite di 20 MB, intervallo minimo di due secondi, user agent
identificabile, nessun redirect automatico e nessun retry su 429 o altri errori.
La lettura di robots è limitata a 512 KB: errori, redirect e contenuti non interpretabili
bloccano il run. L'allowlist impedisce download da altri host o percorsi.
Il crawl-delay dichiarato viene rispettato. L'adattatore non segue paginazione,
feed, avvisi o PDF diversi dagli interventi: un cambiamento del markup senza link
riconosciuti causa errore, non un dataset vuoto di successo.

BeautifulSoup scopre i documenti. PyMuPDF estrae testo ordinato per pagina: non
ricostruisce tabelle, non effettua OCR e non interpreta date di lavori. Documenti
cifrati, oltre 100 pagine, non PDF o senza testo causano errore. Nessun singolo
intervento viene ricavato automaticamente. Prima di costruire un parser tabellare
servono campioni autorizzati e controllo umano dei diversi layout.

Pydantic valida i record; Polars produce CSV/Parquet; JSON conserva i valori null.
DuckDB carica il Parquet in una tabella locale per analisi SQL. L'export sostituisce
il dataset corrente; non è uno storico append-only né una transazione atomica
tra formati. In caso di errore l'output è da rigenerare, non pubblicare.

## Limiti e prossimi passi

Introdurre un livello eventi distinto dai documenti, codici ISTAT verificati,
validazione delle date Europe/Rome, parser per singolo layout, riconciliazione dei
ripristini e revisioni umane tracciate. Aggiungere test su fixture reali soltanto
quando il riuso è autorizzato. Non classificare automaticamente tramite parole
chiave: negazioni, previsioni e comunicati riepilogativi generano falsi positivi.

## Licenze delle dipendenze

Il codice Vinnioi rimane MIT. PyMuPDF è distribuito con opzioni AGPL/commerciali:
https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright
L'uso come dipendenza non assegna la MIT alla libreria. Prima della distribuzione
integrata o dell'esposizione di funzionalità server verificare compatibilità e obblighi
AGPL; valutare un parser alternativo se necessario. Nessuna licenza a pagamento
acquistata. Questo repository non include binari o documenti di terzi.

## Estensione Phase 2

La CLI documentale originale rimane disponibile. `vinnioi-history` aggiunge il flusso:

PDF locale o fonte approvata → parser geometrico → validazione e quarantena →
transazione DuckDB → osservazioni e proiezione → report → snapshot locali.

Il parser Phase 1 resta testuale. Quello Phase 2, in `table_parser.py`, riconosce
specificamente le tabelle degli interventi; non interpreta comunicati o turnazioni.
`quality.py` applica controlli deterministici, ripetuti prima della persistenza.
`store.py` separa municipalities, sources, source_documents, interventions,
intervention_observations e ingestion_runs, aggiungendo membership per URL,
review_records e quality_reports. `datasets.py` esporta le viste e le tabelle.

`pytz` è esplicita dipendenza runtime perché DuckDB la richiede per restituire
TIMESTAMPTZ all'API Python; i timestamp applicativi restano UTC.
L'anagrafica amministrativa ISTAT è distribuita come risorsa del package con fonte,
hash e attribuzione CC BY 4.0; non descrive la copertura effettiva AICA.

Le regole di tempo, assenza, concorrenza e continuità sono nell'ADR 0002. DuckDB
ha un solo processo scrittore: non lanciare due acquisizioni sullo stesso file.
La CI non contatta fonti reali. Il workflow reale è protetto da registro e variabili
SOURCES_VERIFIED/HISTORY_STORAGE_VERIFIED ed è solo manuale. L'eventuale archivio
GitHub va autorizzato anche in relazione alla visibilità della repository.

Un errore HTTP, robots o indice non interpretabile dopo l'approvazione della fonte
produce un run failed e un report input_failure, senza riconciliare assenze. Gli
errori di parsing PDF sono conservati nei report documentali; la CLI ritorna 2.

## Estensione Phase 3

Schema 3 additivo e transazionale. I parser Phase 1/2 restano disponibili; nessuna
riscrittura del frontend. `events.py` estrae comunicati AICA/avvisi Siciliacque da
strutture HTML qualificate e classifica formule operative con regole deterministiche.
`turnations.py` gestisce comuni, sottozone, celle, date esplicite e versioni di calendario.
`source_http.py` riusa i controlli HTTP della pipeline con approvazioni per canale.

`integration_store.py` separa water_events, event_observations, event_municipalities,
water_turnations, turnation_observations ed event_source_links. Le proiezioni degli
eventi narrativi e dei calendari conservano anche needs_review, esplicitamente marcati;
non rappresentano eventi validati sul campo. Le loro osservazioni restano immutabili.
Source_documents e ingestion_runs sono condivisi, senza mescolare real e synthetic.
Gli articoli non operativi sono ignorati con conteggio; errori di parsing e acquisizione
sono riportati nei run. Il modello non registra un evento per ogni articolo editoriale.

`review.py` gestisce decisioni esplicite sulla quarantena tecnica e ne registra il run;
`correlations.py` conserva motivazioni e versioni per associazioni candidate. Nessuna
propagazione di stato tra fonti. `coverage.py` registra evidenze documentali e mantiene
separata la copertura amministrativa dalla gestione contrattuale, non ancora certificata.

`backup.py` implementa il protocollo di storage locale e il restore verificato.
`frontend_data.py` produce un contratto tipizzato di anteprima, senza indirizzi tecnici
o corpo degli articoli. Il flag di pubblicazione rimane false. Gli export completi
sono locali e non devono essere esposti dal frontend. Strategie e limiti sono in
storage.md, revisione.md, licenze-sicurezza.md e nell'ADR 0003.
