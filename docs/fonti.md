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
