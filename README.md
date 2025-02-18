# ProgettoDL - Assistente di Viaggio Intelligente

## Descrizione

Questo progetto implementa un assistente di viaggio intelligente basato su AI e API esterne per aiutare gli utenti a pianificare i loro viaggi in modo semplice ed efficiente. L'assistente è in grado di elaborare richieste in linguaggio naturale e fornire informazioni dettagliate su voli, hotel e attrazioni turistiche.

L'integrazione di LangChain, Google Generative AI (Gemini), RapidAPI e DuckDuckGo Search API permette di gestire in modo efficace le richieste dell'utente, analizzarle e restituire risultati pertinenti e aggiornati.

## Tecnologie Utilizzate

- **Python**: Linguaggio di programmazione principale
- **LangChain**: Per la gestione degli agenti intelligenti e l'orchestrazione delle query
- **Google Generative AI (Gemini)**: Per l'analisi del linguaggio naturale
- **RapidAPI**: Per l'accesso ai dati di SkyScanner e TripAdvisor
- **DuckDuckGo Search API**: Per la ricerca delle attrazioni turistiche
- **Pandas**: Per la formattazione e presentazione dei dati
- **dotenv**: Per la gestione delle variabili d'ambiente
- 
## Esempi di Query
L'assistente di viaggio può rispondere a richieste formulate in linguaggio naturale come:

* Search for a flight from Rome to Madrid from March 7th, 2025 to March 9th, 2025.*
* Show me available flights from Milan to London from September 12th, 2025 to September 18th, 2025.*
  
## Configurazione delle Variabili d'Ambiente

L'assistente richiede un file `.env` contenente le chiavi API necessarie per funzionare correttamente. Crea un file `.env` nella root del progetto e aggiungi:

```plaintext
GEMINI_API_KEY=tuo_api_key
RAPID_API_KEY=tuo_api_key

