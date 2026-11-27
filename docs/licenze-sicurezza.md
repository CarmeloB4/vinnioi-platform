# Licenze, livelli dei dati e sicurezza

Verifica: 27 novembre 2026. La licenza MIT del progetto è invariata e non si estende
ai contenuti AICA/Siciliacque o alle dipendenze. L'anagrafica ISTAT conserva la propria
attribuzione CC BY 4.0. Non vengono pubblicati documenti reali o testi integrali.

## Fonti

Le pagine [privacy AICA](https://www.aicaonline.it/privacy-policy-sito/) e
[privacy/cybersecurity Siciliacque](https://www.siciliacque.it/privacy-cyber-security/)
consultate non qualificano una licenza aperta per i contenuti operativi. La lettura
pubblica e robots.txt non autorizzano automaticamente acquisizione periodica o
redistribuzione. I tre nuovi canali hanno flag separati, tutti false; l'approvazione
del vecchio canale PDF non li abilita. Nessun contatto è stato inviato agli enti.

Per l'acquisizione sistematica occorre documentare termini applicabili, percorsi,
frequenza, attribuzione e condizioni di riuso, eventualmente chiarendole con la fonte.
Non è stata certificata una licenza di redistribuzione dei dataset AICA/Siciliacque.
Gli hash e i conteggi dei report sono metadati di verifica tecnica, non un archivio
degli articoli, indirizzi o eventi reali distribuiti.

## Tre livelli separati

1. Originali: byte HTML/PDF in memoria o in input locali espliciti, fuori da Git;
   nessun caricamento automatico di documenti su storage esterno.
2. Normalizzati: database, payload, evidenze brevi, riferimenti temporali e quarantena
   negli export locali. Possono contenere informazioni da minimizzare: non pubblicarli.
3. Contratti per il futuro frontend: niente testo del corpo, evidenze o civici tecnici;
   publication_approved=false. Titoli e note richiedono ancora una verifica umana di
   minimizzazione prima di qualsiasi pubblicazione reale. Le fixture sono sintetiche.

Il codice non effettua caricamenti pubblici. La classificazione automatica non basta
per pubblicare, rimuovere controlli o trattare un dato come verifica indipendente.
I termini di potabilità sono etichette di dichiarazioni della fonte, non un giudizio
sanitario del progetto. Calendari programmati non certificano erogazione effettiva.

## PyMuPDF e alternative

La [documentazione ufficiale PyMuPDF](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)
indica AGPL o licenza commerciale. Mantenere i file Vinnioi sotto MIT non annulla gli
obblighi della dipendenza. Prima di redistribuire un pacchetto integrato o esporre un
servizio basato su PyMuPDF occorre qualificare gli obblighi applicabili alla soluzione,
inclusi sorgenti e avvisi richiesti dalla licenza scelta. Non è stata acquistata una
licenza commerciale e non è stato esposto un servizio di parsing pubblico.

Valutazioni tecniche svolte senza cambiare lo stack di produzione:

| Opzione | Licenza primaria verificata | Verifica effettiva |
| --- | --- | --- |
| PyMuPDF | AGPL/commerciale | Parser geometrico esistente e regressioni mantenuti. |
| pypdf | [BSD-3-Clause](https://github.com/py-pdf/pypdf/blob/main/LICENSE) | Prova temporanea con versione 7.2.0: letto il campione Agrigento di 31 pagine, testo della prima pagina estratto e identificativo della fonte preservato. Non verificata parità di celle e parser tabellare. |
| pdfplumber | [MIT](https://github.com/jsvine/pdfplumber/blob/stable/LICENSE.txt) | Licenza e possibilità di alternativa valutate; nessun adapter o benchmark implementato in questa fase. |

La prova pypdf usa un ambiente uv temporaneo; nessuna nuova dipendenza PDF è aggiunta
al lockfile. Non sostituiamo un parser funzionante senza verificare parità su celle,
continuazioni, codici e layout. Raccomandazione Phase 4: adapter PDF sostituibile e
confronto su campioni autorizzati prima di decidere distribuzione o migrazione.

## Controlli tecnici

HTTP con host/percorsi ammessi, niente query arbitrarie, redirect automatici o retry;
timeout, limiti di dimensione, intervallo minimo e controllo robots. HTML selezionato
per contenuto operativo, senza navigazione, form, script, footer e contatti generici.
L'assenza di un layout riconosciuto produce un errore, non un evento di ripristino.

La revisione impone hash del payload, URL del documento e motivazione. Gli snapshot
non sono sovrascritti. Backup e restore verificano percorsi e integrità. Non ci sono
credenziali nel codice e non sono introdotti LLM o servizi a pagamento.
