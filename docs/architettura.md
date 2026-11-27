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
