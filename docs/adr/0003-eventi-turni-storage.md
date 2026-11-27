# ADR 0003 — Eventi, calendari, correlazioni e conservazione

Data: 2026-11-27. Stato: accettata.

## Separazione delle informazioni

Aggiungiamo eventi da articoli e osservazioni per singola fonte, senza trasformare
lavori tecnici in disservizi. L'identità iniziale di un evento combina ente e URL
articolo. Due articoli sullo stesso fatto restano due eventi fonte; la correlazione
propone una relazione, non un'identità certa. Source_documents conserva hash dei
byte, osservazioni e payload conservano la versione del parser e il tempo di acquisizione.
Nessun documento originale è distribuito.

L'estrazione usa regole deterministiche con negazioni, previsioni e formule di
conferma separate. La classificazione resta una lettura della fonte: rule_based
non è una probabilità né una verifica indipendente. Un riferimento comunale dentro
il nome di una condotta non è impatto territoriale. Le menzioni e l'area di servizio
esplicita hanno relazioni diverse. Il livello rete è ricavato da evidenza lessicale,
non dal solo ente. Gli orari previsti non diventano tempi effettivi.

## Turnazioni

Una cella è un'osservazione di programma, anche se vuota. Date complete sono accettate
solo se presenti nella fonte. Non si completano giorno/mese/anno usando il download.
Per calendari privi di date complete l'identità include la versione hash: non si
correlano automaticamente “Ven 20” di mesi diversi. Le modifiche sono confrontabili
in modo stabile quando la data è completa; negli altri casi rimane lo storico per
versione. Le assenze sono riconciliate solo per calendari completi e validati e non
provano mancata erogazione o cancellazione del servizio.

## Migrazione e revisione

Schema DuckDB 3: migrazione additiva e transazionale da 2, senza cancellare osservazioni
o promuovere record in quarantena. Nuovi campi di indirizzo separano stringa originale,
civico e qualità. Il segnaposto terminale 99999 non invalida da solo un intervento.
Le vecchie quarantene richiedono decisione esplicita e tracciata; vedere revisione.md.

## Correlazioni

Confronto tra enti diversi con comuni menzionati, nomi di condotte, intervalli di date,
categorie e Jaccard sui token del titolo. Occorrono comuni in comune e almeno una
corrispondenza temporale o di condotta. Punteggio e motivazioni restano candidati;
non si fondono eventi, non si propagano stati e non si deducono guasti a comuni non
citati. Il punteggio è una priorità di revisione, non una probabilità.

## Storage e pubblicazione

Protocollo di storage indipendente dal provider, implementazione locale testata;
nessuna attivazione esterna. I backup includono DuckDB e snapshot Parquet, con
verifica di contenuto, hash e restore separato. Il workflow reale è sospeso finché
non integra storage durevole, evitando artefatti Actions come unico archivio.

Gli export completi sono locali; il contratto frontend è un'anteprima minimizzata
con publication_approved=false. Solo fixture sintetiche sono incluse nell'app.
Nessuna dashboard è sviluppata. Licenze di riuso e revisione dei dati personali
rimangono prerequisiti distinti dalla validazione strutturale.
