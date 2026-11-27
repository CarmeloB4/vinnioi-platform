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
