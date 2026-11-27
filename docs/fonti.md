# Censimento e verifica delle fonti

Verifica iniziale: **27 novembre 2026**. Le pagine indicate sono state consultate
come fonti primarie. L'identificazione della fonte e la verifica tecnica sono
separate dall'approvazione di acquisizione sistematica e riuso, ancora sospesa.

| Fonte | Pagine verificate e ruolo | Formato e limiti | Esito operativo |
| --- | --- | --- | --- |
| AICA | [Interventi programmati](https://www.aicaonline.it/interventi-programmati/), [sito](https://www.aicaonline.it/), [privacy](https://www.aicaonline.it/privacy-policy-sito/) | HTML con PDF per comune; avvisi e comunicati separati. Collegamenti PDF stabili possono cambiare contenuto. La privacy consultata non fornisce una licenza esplicita dei PDF. | Adattatore implementato, acquisizione sistematica e redistribuzione non approvate. |
| Siciliacque | [Sito](https://www.siciliacque.it/), [FAQ](https://www.siciliacque.it/faq/), [comunicati](https://www.siciliacque.it/comunicati-stampa/) | La FAQ descrive la comunicazione dei lavori e dei tempi previsti. I tempi previsti non confermano il ripristino. Non identificata una licenza esplicita dei contenuti nelle pagine consultate. | Censita, adattatore da realizzare dopo verifica condizioni. |
| ATI AG9 | [Sito istituzionale](https://www.atiag9.it/), [identificazione IPA](https://www.indicepa.gov.it/ipa-portale/consultazione/responsabile-transizione-digitale/ricerca-responsabile-transizione-digitale/scheda-ente/1166) | Ente di governo dell'ambito; atti e pianificazione, non fonte assimilabile a un feed di guasti. Non identificata una licenza esplicita nelle pagine consultate. | Censita, nessuna acquisizione periodica. |
| Regione Siciliana | [Osservatorio utilizzi idrici](https://www.regione.sicilia.it/istituzioni/regione/strutture-regionali/presidenza-regione/autorita-bacino-distretto-idrografico-sicilia/osservatorio-distrettuale-permanente-sugli-utilizzi-idrici), [note legali](https://www.regione.sicilia.it/note-legali) | Disponibilità e uso della risorsa, report e documenti. Le note legali pongono condizioni al riuso: verificare ogni dataset, titolarità e attribuzione; non applicare una licenza generalizzata agli allegati. | Censita, selezione dei dataset e verifica licenze ancora necessarie. |

## Robots e comportamento HTTP

`docs/robots-audit.json` registra status e hash delle risposte ricevute durante la
verifica tecnica. AICA vieta la directory degli allegati dell'albo pretorio, che il
nostro adattatore non visita. Siciliacque esclude cgi-bin; ATI esclude wp-admin;
Regione richiede crawl-delay 10 secondi ed esclude percorsi amministrativi e alcune
query. Tutte le risposte osservate erano HTTP 200. Ricontrollare a ogni run:
robots non costituisce autorizzazione al riuso e può cambiare.

Non sono state aggirate autenticazioni, protezioni o limitazioni. I contenuti reali
consultati per l'ispezione non sono inclusi nella repository. Nessuna API stabile è
stata qualificata per l'integrazione: questa verifica non dimostra che non esistano API.

## Verifica tecnica AICA

La scoperta ha riconosciuto 30 collegamenti PDF coerenti con il percorso
`/interventi_programmati/interventi_*.pdf`. Un solo PDF, quello di Agrigento,
è stato scaricato per ispezione temporanea: 31 pagine, testo estraibile, hash
`abb5a50a110ce5543caf7584ec4256af8f1d769453ca3c37c0837f92ad26b7fb`.
L'estrazione mostra tabelle con codici, indirizzi, tipo/rete, stato e impatto.
Non si assume che tutte le righe siano incidenti o ripristini, né che tutti i PDF
abbiano lo stesso layout. Il timestamp di generazione del documento non coincide
necessariamente con pubblicazione o data dell'intervento. L'ispezione non autorizza
la ripubblicazione del documento o dei suoi indirizzi.

## Condizioni per l'attivazione

Prima di modificare `acquisition_approved` in `config/sources.toml`:

1. Registrare URL e data delle condizioni applicabili, finalità, frequenza e percorsi.
2. Chiarire il permesso di acquisizione automatica; se necessario contattare la fonte.
3. Accertare separatamente licenza e condizioni di riuso dei metadati/estratti.
4. Revisionare dati personali, minimizzazione e attribuzione; non caricare PDF su Git.
5. Verificare altri layout, stato dichiarato e significato delle date su campioni autorizzati.
6. Eseguire test offline e un'acquisizione limitata controllata; revisionare i risultati.
7. Solo dopo approvazione documentata, impostare SOURCES_VERIFIED=true nelle variabili
   repository e attivare il cron tramite PR dedicata. Il cron proposto è 05:17 UTC.

L'attivazione dell'acquisizione non autorizza la pubblicazione: gli export restano
in staging e `redistribution_allowed` resta false. Il workflow non carica artefatti.

## Analisi AICA — Phase 2 (27 novembre 2026)

| Sezione | Layout e informazioni osservate | Frequenza e criticità |
| --- | --- | --- |
| [Interventi](https://www.aicaonline.it/interventi-programmati/) | Indice di PDF comunali; campioni Agrigento, Aragona e Ribera con sei colonne: posizione, codice intervento, indirizzo, tipo/rete, stato, impatto. | Timestamp di generazione nel PDF, non pubblicazione. Nessuna frequenza garantita accertata. URL sostituibili, righe tra pagine, indirizzi segnaposto. |
| [Comunicazioni](https://www.aicaonline.it/comunicazioni/) | Archivio HTML paginato, date editoriali, titoli e testi narrativi; include comunicazioni non operative e riepiloghi. | Date editoriali irregolari osservate; nessun SLA accertato. Previsioni e riepiloghi non sono singoli interventi o conferme di ripristino. |
| [Turni](https://www.aicaonline.it/servizi/turni-idrici-settimanali/) | La pagina di servizio rimanda a [turni-idrici-2](https://www.aicaonline.it/turni-idrici-2/), una pagina HTML con comuni, serbatoi, zone, vie e colonne giornaliere. | La denominazione settimanale non prova una frequenza di aggiornamento garantita. Celle vuote, rinvii e orari richiedono uno schema specifico; un turno non equivale a erogazione effettiva. |

L'ispezione è stata limitata alla lettura delle pagine indicate e di tre campioni
PDF (uno già disponibile temporaneamente dalla Phase 1). Non è stata abilitata
acquisizione sistematica; l'allowlist operativa resta limitata agli interventi.
I campioni reali restano fuori dalla repository; si riportano solo metriche tecniche
aggregate, senza indirizzi, righe o testo dei documenti. Resta non qualificata la
licenza per pubblicare i dataset derivati AICA.

## Anagrafica amministrativa ISTAT

Fonte ufficiale: [classificazione territoriale](https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/)
e [CSV ISTAT](https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv),
acquisito il 27 novembre 2026. Le [note legali ISTAT](https://www.istat.it/note-legali/)
indicano CC BY 4.0 salvo diversa specifica. Il sottoinsieme AG contiene 43 comuni;
abbiamo selezionato codici e nomi ufficiali, mantenendo gli zeri iniziali come stringhe.
Fonte, hash originale, trasformazione e attribuzione sono nel file provenance della
risorsa del package. L'elenco non autorizza inferenze sulla copertura effettiva AICA.

## Workflow storico, ancora disabilitato

Oltre alle condizioni già elencate, la conservazione di database ed export come
artefatti GitHub richiede una valutazione della visibilità della repository e del
riuso degli indirizzi. HISTORY_STORAGE_VERIFIED deve rimanere non attiva fino a tale
verifica. Il registro deve consentire sia acquisizione sia redistribuzione per quel
workflow. La CLI locale non pubblica nulla e può essere usata per campioni già
legittimamente disponibili, registrando il tempo effettivo di osservazione.

Il workflow manuale richiede previous_run_id per scaricare il database precedente;
solo la prima esecuzione può usare initialize_history=true. Un artefatto mancante
causa errore e non avvia uno storico nuovo. La retention di 30 giorni richiede backup
esterno approvato e una procedura per la continuità. Il cron non si abilita finché
non sono risolti storage durevole e recupero dello storico. Nessun workflow reale
è stato avviato durante questa fase.

## Phase 3: canali qualificati e copertura osservata

La nuova CLI separa aica_communications, siciliacque_notices e aica_turnations;
tutti restano non approvati. La qualifica tecnica comprende gli indici HTML AICA
(10 collegamenti nella prima pagina) e [avvisi Siciliacque](https://www.siciliacque.it/avvisi/)
(12 collegamenti), un articolo operativo per ente e la struttura dei calendari.
Non è una scansione completa degli archivi. I nuovi PDF campione sono Sciacca
(214 righe) e Licata extra urbana (3 righe). La variante del titolo extraurbano è
accettata solo in corrispondenza del comune Licata e del relativo URL specifico.

Il calendario osservato contiene blocchi per 33 comuni ISTAT riconosciuti, mentre
l'indice PDF ne contiene 29 unici. Le sottozone esplicitamente intitolate AGRIGENTO
mantengono il comune e una district separata; UTENZE VOLTANO resta senza comune.
La pagina [L'Azienda](https://www.aicaonline.it/lazienda/) elenca i comuni fondatori,
non un perimetro contrattuale corrente certificato. Non si sovrappongono questi
elenchi e non si marca la copertura amministrativa come copertura del gestore.

I comuni coinvolti negli eventi sono estratti dal contenuto operativo. I nomi nelle
condotte composte non attribuiscono impatto. Siciliacque è trattata con evidenza di
adduzione quando il testo parla di acquedotti/adduttori, senza dedurre interruzioni
nella distribuzione locale o estenderle ai comuni della condotta non citati.

Risultati, hash e anomalie sono in docs/phase3-verifica.md e nel report tecnico.
Le pagine privacy consultate non forniscono una qualifica di riuso dei contenuti:
vedere licenze-sicurezza.md. Gli originali e le righe reali restano fuori da Git.

**Sospensione del workflow reale:** il precedente flusso di passaggio del database
tra artefatti Actions non può essere l'unico archivio. In Phase 3 è bloccato con
if: false. Non basta impostare le variabili precedenti: per riattivarlo serve una
PR con storage durevole integrato e testato, condizioni delle fonti e backup/restore.
La raccolta locale esplicita rimane subordinata al registro del singolo canale.
