# ADR 0001 — Monorepo e acquisizione conservativa

Data: 2026-11-27. Stato: accettata.

Usiamo uv/Python 3.12 per il package dati e npm workspaces per Astro statico.
I lockfile sono versionati; i risultati e documenti locali restano fuori da Git.
Si evita infrastruttura operativa prima di disporre di dati affidabili.

Il primo livello dati descrive documenti programmati AICA, senza simulare eventi.
L'estrazione PDF è testuale e richiede revisione; stato e date sconosciuti restano null.
Questa scelta riduce copertura iniziale ma permette di verificare la provenienza.

Gli aggiornamenti hanno due blocchi: registro di acquisizione e variabile repository
SOURCES_VERIFIED. Il cron resta commentato; nessun upload automatico degli output.
L'attivazione avviene con PR dedicata e motivazione sulle condizioni delle fonti.

Il frontend statico usa Tailwind 4 con plugin Vite e nessun adapter Cloudflare SSR:
può essere pubblicato su Pages senza funzioni o servizi aggiuntivi. Non viene deployato
in questa fase. Tutte queste scelte sono reversibili senza migrare dati pubblici.

I lockfile devono usare registri pubblici: npmjs.org e pypi.org. Il registro npm
è esplicitato in .npmrc per evitare che configurazioni locali di mirror autenticati
rendano la CI dipendente dall'ambiente dello sviluppatore. L'installazione pulita
con npm ci verifica anche gli hash dei pacchetti sul registro pubblico.
