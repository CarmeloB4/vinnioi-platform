# ADR 0002 — Interventi, osservazioni e quarantena

Data: 2026-11-27. Stato: accettata.

## Identità e tempo

Un intervento è identificato da SHA256([source_id, municipality_istat_code,
source_intervention_id]). Lo scope comunale evita di presumere che il codice della
fonte sia globalmente unico. URL e hash dei byte identificano la versione documentale.
Ogni run crea osservazioni immutabili e aggiorna una proiezione corrente: rileggere
lo stesso hash non crea un altro documento, ma conferma la presenza e last_seen_at.

Il replay con stesso run_id, timestamp e contenuto è idempotente. Un run_id riusato
con altro contenuto è errore. Le acquisizioni sono ordinate nel tempo; i backfill
si elaborano separatamente per non sovrascrivere lo stato corrente con dati vecchi.
Non esiste un'identità stabile inventata per righe senza codice della fonte.

## Estrazione e validazione

Usiamo il layout tabellare osservato con sei colonne, griglia riconosciuta da
PyMuPDF e parole assegnate geometricamente alle celle. Evitiamo l'estrazione del
codice dal solo testo della tabella: nel campione può spezzare il carattere underscore.
Gestiamo continuazioni tra pagine limitate al nome rete; altre continuazioni dubbie
producono errori. Totale dichiarato, intestazioni e titolo comunale sono controllati.

La validazione strutturale non certifica il fatto sul campo. Lo stato COMPLETATO
non conferma un ripristino. Stati non riconosciuti sono conservati in quarantena.
Indirizzi con 99999 non vengono corretti: sono segnaposto da revisionare.
La conferma esplicita può essere osservata anche senza data di risoluzione:
restoration_confirmed=true, resolved_at=null. Nessuna data è imputata.

## Persistenza ed export

DuckDB è il sistema locale di registrazione, con schema versione 2 e transazione
per batch. Le chiavi e i vincoli di consistenza dei riferimenti sono verificati
nell'applicazione e nei test; non usiamo foreign key DuckDB per la proiezione aggiornata.
I run falliti sono registrati, ma le loro scritture dati sono annullate.
Le righe in quarantena hanno posizione nel PDF, provenienza e motivi di revisione.

La scomparsa è una nuova osservazione di assenza, limitata allo stesso URL: non
modifica lo stato dichiarato, last_seen_at o resolved_at. Un documento con errori o
quarantena non può dimostrare assenze. Le osservazioni contraddittorie di uno stesso
intervento nel medesimo batch sono tutte messe in revisione.

Gli export sono directory snapshot immutabili. Il puntatore LATEST cambia solo a
scrittura completata; un errore di export non annulla lo storico DuckDB, riesportabile.
Parquet conserva tipi e timestamp. CSV usa il marcatore null \\N e JSON conserva null.

## Continuità operativa

GitHub Actions supporta il ripristino esplicito del database da un run precedente,
o un'inizializzazione dichiarata, mai un nuovo storico vuoto silenzioso. Gli artefatti
hanno conservazione limitata a 30 giorni: non sostituiscono un archivio durevole.
Il cron resta spento; occorre definire backup e continuità prima dell'attivazione.
Nessun costo, deploy, LLM o modifica funzionale del frontend introdotto.
