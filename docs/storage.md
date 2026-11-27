# Storage e continuità operativa — Phase 3

Stato al 27 novembre 2026: implementati e testati **solo storage e restore locali**.
Nessun bucket, account, Release, client remoto o servizio a pagamento è stato attivato.
Gli artefatti Actions sono utili per diagnostica, non un archivio durevole.

## Interfaccia e implementazione

`backup.Storage` espone `put(key, bytes)` e `get(key)`. `LocalStorage` implementa
oggetti immutabili con creazione esclusiva, percorsi confinati nella directory
configurata e fsync. Ogni backup ha UUID, database DuckDB e snapshot degli export
CSV/JSON/Parquet con manifest SHA-256 e dimensioni. Il manifest finale è scritto per
ultimo: un errore durante il salvataggio non produce un backup completo valido.
Oggetti parziali restano da ispezionare, senza cancellazioni automatiche.

Il database deve essere chiuso e senza WAL pendente. Un lock DuckDB read-only evita
scrittori concorrenti; un writer aperto impedisce il backup. Per ogni dataset si
confrontano entrambe le differenze SQL EXCEPT ALL tra database e Parquet: stesso
numero di righe non basta a dimostrare la coerenza dello snapshot. Si salva il file
DuckDB solo dopo questi controlli. Serve un singolo processo di manutenzione;
non modificare i file degli export durante il backup.

Il restore verifica percorsi, lunghezze, hash, apertura del database e versione
schema, in una directory temporanea poi rinominata. Non sovrascrive una destinazione
esistente. Gli hash rilevano corruzione, non autenticano un manifest ostile: usare
solo backup da storage fidato, con accessi controllati. I dati locali non sono cifrati
dall'applicazione; usare dischi cifrati e permessi del sistema operativo appropriati.

```sh
uv run vinnioi-history --database data/history/vinnioi.duckdb --export-only
# Terminare tutti i writer e sostituire SNAPSHOT_ID con lo snapshot indicato da LATEST.
uv run vinnioi-integrate backup --database data/history/vinnioi.duckdb \
  --snapshot data/exports/SNAPSHOT_ID --storage data/backups
uv run vinnioi-integrate restore --backup-id BACKUP_UUID \
  --storage data/backups --destination data/restored
```

I backup su un solo disco non proteggono da perdita del computer. La strategia
proposta è 3 copie, 2 supporti, 1 copia fuori sede; conservazione suggerita di
7 giornalieri, 8 settimanali e 12 mensili, da dimensionare sui dati effettivi.
Prima di migrare un database esistente fare un backup e provarne il ripristino.
RPO/RTO iniziali proposti: 24 ore / un giorno lavorativo, **non ancora garantiti**.
Provare periodicamente il restore in una directory distinta e confrontare conteggi,
versione schema e query dello storico. Nessuna politica di eliminazione automatica
è implementata in questa fase.

## Valutazione delle opzioni esterne

| Opzione | Costi e limiti verificati | Uso proposto e limiti operativi |
| --- | --- | --- |
| Cloudflare R2 Standard | Listino: 0,015 USD/GB-mese, 4,50 USD/milione operazioni A e 0,36 USD/milione B; franchigia mensile 10 GB-mese, 1 milione A e 10 milioni B; egress gratuito. | Candidato per snapshot privati immutabili, manifest e copia fuori sede. Servono account autorizzato, gestione chiavi, budget e adapter testato; non configurato. |
| S3-compatible | S3 è un protocollo, non un prezzo unico: costo del provider o dei dischi, richieste, recupero e traffico dipendono da servizio, regione e classe. | Valutare versioning, retention, controllo accessi e copia indipendente. Un servizio self-hosted richiede comunque manutenzione e backup dei dischi. Nessun endpoint o SDK configurato. |
| GitHub Releases | La documentazione indica massimo 1.000 asset per release, ogni file sotto 2 GiB, nessun limite aggregato dichiarato di dimensione release/banda. | Solo snapshot autorizzati e minimizzati. La visibilità segue la repository: non caricare dati riservati o documenti senza licenza. Non sostituisce un backup privato indipendente. Nessuna Release creata. |

Esempio puramente indicativo R2: 20 GB-mese Standard conservati, con operazioni entro
le franchigie, implicano circa 0,15 USD/mese per il solo storage eccedente i 10 GB.
Non include imposte, arrotondamenti, altri servizi o richieste oltre franchigia e non
costituisce autorizzazione a sostenere costi. La classe Infrequent Access ha costi
di recupero e non usa la franchigia Standard: non è scelta per questo progetto.

Fonti primarie consultate: [R2 pricing](https://developers.cloudflare.com/r2/pricing/),
[S3 pricing](https://aws.amazon.com/s3/pricing/),
[GitHub Releases e quote](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).
Le cifre vanno ricontrollate prima di attivare un servizio.

## Workflow reale

Il workflow Phase 2 è ora bloccato con `if: false`, oltre al cron già commentato.
Motivo: il solo passaggio tra artefatti Actions non assicura durata dello storico.
Prima di riattivarlo servono licenze e condizioni delle fonti, storage durevole
approvato, integrazione dell'adapter, prove di backup/restore, continuità dei run e
budget. Nessun adapter remoto è dichiarato operativo da questa PR.
