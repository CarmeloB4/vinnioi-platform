# ADR 0004 — Portale statico, modalità esplicite e confini territoriali

Data: 2026-11-27. Stato: accettata.

## Decisione

Manteniamo Astro, TypeScript strict e Tailwind 4. Generiamo HTML statico per tutte
le pagine comunali, dettagli, metadati e download ammessi. Niente server applicativo,
account utente, analytics, cookie di tracciamento o servizi a pagamento. Inter è
servito localmente. Palette e spaziature sono token CSS; il nome testuale è uno slot
sostituibile dal logo ufficiale, non una proposta di marchio.

Il modello frontend riusa il contratto Phase 3 e lo valida con Zod solo in build.
I moduli client importano helper e tipi separati dalla validazione per evitare
l'inclusione di Zod nel bundle dei filtri. Le estensioni opzionali `declared_status`
e `restoration_expected_on` permettono di illustrare gli stati previsti senza
modificare il parser o dedurre date mancanti nelle fonti reali.

## Confine di pubblicazione

La modalità predefinita è production. Senza input operativo autorizzato le pagine
mostrano dati mancanti, copertura sconosciuta e nessuno stato di servizio dedotto.
La demo richiede una scelta esplicita, un banner su tutte le pagine e noindex;
non è ammessa su main Cloudflare o una destinazione dichiarata production.

Un input reale deve superare validazione strutturale, coerenza fonte/URL, controllo
di unicità dei permalink e revisione. Richiede inoltre un'autorizzazione separata
legata all'hash SHA-256 dei byte e permessi di redistribuzione per ogni fonte.
Questo manifest è un'attestazione del processo di revisione, non una firma digitale
né una verifica automatica della validità giuridica delle licenze. La pipeline
esistente continua a produrre anteprime non approvate: nessun flag viene promosso
automaticamente. Storage durevole e condizioni delle fonti rimangono aperti.

## Mappa e semantica

MapLibre viene caricato solo su richiesta. Mostra poligoni ISTAT generalizzati
2026, riproiettati in EPSG:4326: nessun geocoding o punto inventato, nessuna tile
esterna. Le isole sono comprese; una vista iniziale della Sicilia e un controllo
esplicito evitano una scala illeggibile. L'elenco HTML dei 43 comuni è l'alternativa
accessibile e rimane disponibile in caso di errore o WebGL assente.

Il colore indica la presenza di eventi nel dataset, mai la regolarità del servizio.
Lavori tecnici, dichiarazioni di ripristino e previsioni restano distinti. Le
turnazioni compaiono soltanto se validate e con data completa. I grafici sono liste
con etichette e valori testuali; i filtri usano la data editoriale, non la durata
del disservizio. I conteggi non deduplicano eventi di fonti diverse.

## Conseguenze

Cloudflare Pages può ospitare l'output senza adapter SSR. Aggiornamenti richiedono
una nuova build: non è un monitoraggio in tempo reale. Il bundle MapLibre è più
pesante dei filtri, ma non viene scaricato nella navigazione ordinaria. Non sono
necessari database o segreti nel browser. In Phase 5 serviranno pubblicazione
revisionata, storage verificato, test con tecnologie assistive e misure Lighthouse
su un ambiente di preview autorizzato.
