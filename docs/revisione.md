# Revisione tracciata degli interventi

La quarantena originale in `review_records` non viene cancellata né riscritta.
Ogni decisione registra ID, revisore, data, azione approve/reject, motivazione,
URL del documento originale verificato, hash del payload atteso, regola applicata,
correzioni e payload prima/dopo. Il digest del payload protegge da revisioni obsolete;
non è una firma dell'identità del revisore. Il registro locale dipende dagli accessi
al filesystem: non è una piattaforma con autenticazione multiutente.

Le decisioni sono append-only nell'API. Non si riusa un decision_id, non si revisiona
nuovamente lo stesso review_id: nuove evidenze richiedono una nuova osservazione.
Un rifiuto resta nel registro e non promuove nulla. Un'approvazione deve superare
nuovamente i controlli, senza cancellare gli errori di parsing o i conflitti residui.
Non può alterare provenienza, hash, date della fonte o inventare un identificativo.
I campi correggibili sono codice intervento fonte, comune, indirizzo, tipo intervento,
rete e stato dichiarato. Le correzioni sono affermazioni esplicite del revisore
riscontrate nel documento, non valori ricavati automaticamente.

La promozione genera un run di revisione e un'osservazione riferita al documento
originale. Il tempo della decisione è distinto dal tempo dell'osservazione della fonte.
Non si sovrascrive una proiezione uguale o più recente. Il primo tempo visto nella
proiezione validata non include automaticamente osservazioni precedenti rimaste in
quarantena; la loro provenienza rimane nel registro per la revisione.

```sh
uv run vinnioi-integrate review --database data/history/vinnioi.duckdb \
  --decision data/review/decision.json
```

Il formato è definito in `docs/review-decision.schema.json`; la demo
`scripts/demo_integration.py` esegue una revisione interamente sintetica completa.
Lo strumento di revisione di questa fase riguarda la quarantena degli interventi
PDF. Gli eventi e calendari con needs_review sono conservati come tali; non esiste
ancora una UI o una procedura di approvazione umana delle loro classificazioni.

## Regola AICA-99999-v1

Verifica: campioni delle Phase 2 e 3, incluso controllo visivo del layout extraurbano
Licata e confronto delle celle. Il valore finale isolato `99999` è trattato come
civico non disponibile. La regola si applica solo al suffisso dopo uno spazio:

- address_original conserva esattamente il valore estratto.
- address conserva la via senza quel suffisso; house_number resta null.
- address_quality diventa house_number_unavailable.
- La validità strutturale dell'intervento dipende da identità, comune, rete, tipo,
  stato e provenienza, non dalla disponibilità del numero civico.

Una via o un civico assente non viene completato con dati inventati. Nessun altro
numero viene corretto automaticamente. La qualità as_reported descrive l'estrazione,
non una geocodifica o una verifica dell'indirizzo sul territorio.

Le nuove estrazioni applicano questa regola verificata. La migrazione non promuove
le vecchie quarantene. Per approvare un vecchio record con address_placeholder
occorre una decisione esplicita con rule_id `AICA-99999-v1`, controllo della fonte e
assenza di altre anomalie non risolte. Non è stata eseguita alcuna promozione di dati
reali durante questa fase. Le decisioni dimostrative sono tutte sintetiche.
