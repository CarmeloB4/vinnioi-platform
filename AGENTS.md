# Istruzioni per gli agenti

Scrivere documentazione e messaggi del prodotto in italiano. Il progetto è civico,
indipendente e apartitico. Mantenere la licenza MIT esistente.

## Priorità

1. Provenienza, qualità, verificabilità dei dati.
2. Acquisizione rispettosa delle fonti e tracciamento delle incertezze.
3. Interfaccia accessibile, leggera e senza dati inventati.

## Regole sui dati

- Non inventare eventi o timestamp di pubblicazione. Usare null se sconosciuti.
- Distinguere guasti, attività programmate, turnazioni e ripristini dichiarati.
- Un termine previsto non conferma un ripristino. Un PDF aggiornato non è un nuovo guasto.
- Non dedurre stato del servizio da assenza di avvisi o da lavori eseguiti.
- Non salvare documenti di terzi, dati personali o testo integrale nel repository.
- La raggiungibilità e robots.txt non costituiscono una licenza di riuso.
- Non attivare schedule o pubblicazione senza verifica documentata delle fonti.
- Non aggiungere servizi a pagamento. Decisioni reversibili in docs/adr/.

## Verifica

Python 3.12 e uv; dipendenze bloccate in uv.lock. Dopo modifiche Python eseguire
`uv run ruff check .`, `uv run ruff format --check .` e `uv run pytest`.
Dopo modifiche web eseguire `npm run check` e `npm run build`.
I test devono restare offline, usare fixture sintetiche e coprire errori di formato,
provenienza, regole di classificazione e blocchi di acquisizione.
