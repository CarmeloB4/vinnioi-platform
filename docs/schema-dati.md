# Contratto dati 0.1

`Record` in `models.py` rappresenta una versione di un documento fonte. Non è ancora
un evento operativo. I nomi dei campi e gli enum sono il contratto degli export.

| Campo | Significato |
| --- | --- |
| id | SHA-256 di URL + newline + hash contenuto: stessa versione, stessa identità |
| source, source_url | Ente e collegamento originale |
| discovered_at | Momento di scoperta del collegamento, timezone obbligatoria |
| fetched_at | Momento di acquisizione/estrazione, timezone obbligatoria |
| published_at, event_at | Date dichiarate, null finché non accertate |
| comune, area | Etichetta dal link AICA e sottoarea; non ancora codice ISTAT |
| category | guasto, intervento_programmato, ripristino_confermato, non_classificato |
| declared_status | Stato dichiarato dalla fonte; null se non estratto |
| evidence | Evidenza esplicita breve, necessaria per un ripristino |
| content_sha256 | Hash dei byte PDF originali, consente rilevazione cambiamenti |
| parser_version | Versione della logica di estrazione |
| review_required | True per tutti i record acquisiti automaticamente |
| redistribution_allowed | False finché non autorizzato il riuso del dataset |

Gli interventi AICA sono classificati dalla sezione di provenienza, non dalla
lettura del contenuto. Non sono guasti confermati né lavori in corso. Gli orari
previsti non autorizzano la categoria ripristino_confermato. Anche un ripristino
dichiarato dalla fonte non costituisce una verifica indipendente sul campo.

I tempi generati dalla pipeline sono UTC. Nessuna data è dedotta dall'URL, da PDF
metadata o dal momento del download. Turnazioni e misure di invaso richiederanno
schemi dedicati (periodi, unità, copertura, aggiornamenti), senza forzarli in questo
primo contratto. Gli export non includono il testo delle pagine PDF.

# Contratto Phase 2 — versione 2

Il contratto documentale 0.1 rimane disponibile per compatibilità. Il nuovo contratto
è `Intervention` (`docs/intervention.schema.json`). Ogni riga include i campi richiesti:
intervention_id, source_id, municipality, municipality_istat_code, province, address,
intervention_type, network_type, reported_status, published_at, scheduled_at,
first_seen_at, last_seen_at, resolved_at, source_url, document_hash, extracted_at,
validation_status. Aggiungiamo source_intervention_id, pagina/riga, issues,
restoration_confirmed, category, parser_version e data_origin.

- `source_id`: ente AICA; `source_intervention_id`: codice originale della riga.
- `intervention_id`: chiave Vinnioi, null se non assegnabile con sicurezza.
- `province`: AG se il comune è riconosciuto; altrimenti null.
- `published_at`, `scheduled_at`, `resolved_at`: null per il layout attualmente letto.
  Il timestamp "Generato il" resta stringa documentale separata, non pubblicazione.
- `first_seen_at` e `last_seen_at`: osservazioni della pipeline, non date del lavoro.
- `extracted_at`: momento effettivo di esecuzione del parser, distinto dall'osservazione
  anche nei replay di documenti già acquisiti. Nelle fixture è un tempo simulato esplicito.
- `reported_status`: testo originale normalizzato solo negli spazi.
- `validation_status`: validated oppure needs_review. Non significa verifica sul campo.
- `category`: intervento_programmato, dalla sezione AICA; non equivale a guasto.
- `data_origin`: real o synthetic; vietato mescolarli nello stesso database.

## Entità DuckDB

| Entità | Identità e contenuto |
| --- | --- |
| municipalities | Codice ISTAT VARCHAR a sei caratteri, nome ufficiale, provincia, copertura gestore unknown |
| sources | Ente, URL indice e flag acquisizione/riuso (false per import locali non qualificati) |
| source_documents | URL + hash byte, fonte, comune, layout, timestamp di generazione originale, esito parsing |
| interventions | Proiezione corrente delle sole righe validate; tutti i campi del contratto |
| intervention_observations | ID intervento/documento/run, timestamp, presenza, tipi di variazione e payload osservato |
| ingestion_runs | ID run, fingerprint input, timestamp, origine, stato e tipo errore in caso di rollback |
| document_membership | Ultima presenza osservata per coppia URL/intervento, distinta dallo stato del servizio |
| review_records | Righe dubbie con posizione, provenienza, campi null e motivi di revisione |
| quality_reports | Report per run, conteggi, issue, copertura e completezza |

Le variazioni sono new, known, status_changed, information_changed, missing,
reappeared e restoration_confirmed. Una variazione può avere più etichette.
Le osservazioni mancanti hanno present=false e payload vuoto: non inventano
un'ulteriore dichiarazione della fonte.

## Dataset locali

CSV, JSON e Parquet per interventions, intervention_history, municipalities,
municipality_summary e data_quality_report; inoltre review_records, sources,
source_documents e ingestion_runs per audit. I campi JSON strutturati conservano
payload e motivazioni; in CSV sono celle JSON. Codici ISTAT in Parquet e JSON
restano stringhe (per CSV impostare esplicitamente il tipo quando lo si importa).

municipality_summary distingue copertura gestore sconosciuta, numero di versioni
documentali osservate, interventi noti e conferme esplicite. Non conta "guasti attivi"
né presenta zero interventi come prova di servizio regolare.

## Qualità

`errors` conta errori documentali; `review_records` conta righe in quarantena;
`issue_counts` conta le singole anomalie (una riga può averne più di una).
La completezza di ogni campo è la percentuale di valori non null, non la loro
correttezza. Su zero righe è null. Le date non disponibili possono quindi avere
completezza 0% senza essere errori. La copertura è rispetto ai 43 comuni amministrativi,
non rispetto ai comuni effettivamente serviti. Stato/data di un ripristino non sono
dedotti dalla copertura o dal conteggio delle righe.
