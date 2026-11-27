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

# Contratto Phase 3 — versione 3

Migrazione additiva da schema 2, senza riclassificazione dello storico esistente.
Gli interventi aggiungono area, address_original, house_number e address_quality.
Il suffisso civico 99999 segue AICA-99999-v1; la qualità dell'indirizzo non determina
da sola la validità dell'intervento. I campi nuovi dei record legacy possono essere
null finché non arriva una nuova osservazione o revisione esplicita.

| Entità | Contenuto e separazione |
| --- | --- |
| water_events | Evento fonte identificato da ente + URL articolo; proiezione corrente, categorie, stato dichiarato, affidabilità e payload |
| event_observations | Versione documentale, run, tempo di osservazione, variazione e payload storico |
| event_municipalities | Codice ISTAT, evidenza e relazione explicit_service_area oppure mentioned_only |
| event_source_links | Fonte originale dell'evento; non una fusione fra enti |
| water_turnations | Ultima osservazione dello slot di calendario con data, qualità e payload |
| turnation_observations | Versioni e cambiamenti dello slot; not_in_calendar non significa mancata erogazione |
| review_decisions | Decisioni immutabili nell'API con autore, hash atteso, motivo, fonte, regola e prima/dopo |
| event_correlations | Coppie candidate con hash delle due versioni, score di priorità e motivazioni |
| operator_coverage_evidence | Claim documentale e provenienza; non aggiorna automaticamente la copertura contrattuale |

Gli schemi JSON sono water-event.schema.json, water-turnation.schema.json,
review-decision.schema.json e frontend-water-data.schema.json. Tutti i nuovi oggetti
conservano l'origine real/synthetic. Gli originali non sono inclusi negli export.

## Eventi

Sette categorie: guasto, interruzione, manutenzione_programmata, riduzione_portata,
emergenza_idrica, potabilita e ripristino_confermato. Categorie multiple possono
coesistere nello stesso articolo. declared_status conserva un estratto della
dichiarazione locale e non è un nuovo giudizio sul servizio. published_on è una date; published_at esiste solo con
un timestamp completo e timezone. acquired_at ed extracted_at sono distinti.

Ogni riferimento temporale conserva testo, data se ricavabile, ora se esplicita e
kind planned/actual/unresolved. Oggi/domani usano la data editoriale disponibile;
non la data del download. I riferimenti di ripristino previsti non confermano nulla.
restoration_confirmed indica una formula esplicita della fonte, non un controllo
indipendente e non un ripristino attribuito a tutti i comuni citati. Articoli con
più comuni e ripristino richiedono revisione dello scope.

network_level è adduction, local_distribution oppure unspecified secondo evidenza
lessicale: non dal solo nome dell'ente. reliability è rule_based, needs_review o
human_reviewed; il parser usa le prime due. Nessuna probabilità di accuratezza è
stimata. validation_status riguarda la struttura e le regole, non l'attualità del fatto.

## Calendari

Conservati comune, etichetta originale, sottozona, serbatoio se disponibile, zona,
viabilità, label data originale, data completa se esplicita, fascia oraria, valore
originale, validità dichiarata, note, hash versione e posizione nella fonte.
actual_delivery_confirmed è sempre false per questo contratto.

Con data completa l'identità dello slot non cambia al cambiare dell'orario. Senza
data completa include l'hash del calendario: nessuna falsa continuità fra mesi.
Duplicati conservati con posizione distinta restano in revisione. Le celle vuote
hanno valore e orario null, non uno stato di sospensione inventato.

## Dataset e anteprima

Gli export locali includono tutte le nuove tabelle in CSV/JSON/Parquet, oltre ai
precedenti dataset. Il frontend ha un contratto separato: eventi recenti, eventi per
comune con area esplicita, interventi tecnici senza indirizzi, turnazioni senza vie,
timeline, indicatori dei 43 comuni e stato dell'ultimo tentativo/successo. Gli
indicatori non attestano servizio regolare se i dati mancano. Il flag
publication_approved è false anche per i dati strutturalmente validati.

L'ultimo tentativo e l'ultimo successo non dimostrano freschezza della fonte: se
ci sono errori o revisioni il contratto segnala needs_review. Una revisione umana è
un run distinto e non cambia il tempo di osservazione della fonte originale.

L'anteprima distingue anche last_source_observed_at dall'ultimo run completato:
una revisione umana non rende più recente la fonte. Un ultimo run fallito resta
failed, separato da needs_review per qualità o classificazione.
