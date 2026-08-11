# Cinema Social Media Manager Agent

Sistema multi-agente basato su **LangGraph** che genera automaticamente post Instagram per un cinema:
cerca notizie/uscite cinematografiche, seleziona gli spunti migliori, scrive la caption, genera l'immagine
coerente col brand, e salva tutto pronto per la pubblicazione.

Migrato da un prototipo iniziale su Google ADK + Gemini a **LangGraph + OpenAI**, con generazione immagini
via **gpt-image-2**.

## Architettura

```mermaid
flowchart TD
    S([START]) -->|mode: generic_news| DGN[discover_generic_news]
    S -->|mode: movie_release| DMR[discover_movie_releases]
    DGN --> SEL[select_items]
    DMR --> SEL
    SEL -->|selezione vuota, tentativi rimasti| REF[refine_query]
    SEL -->|selezione ok o tentativi esauriti - Send per item| PI[process_item]
    REF -->|mode: generic_news| DGN
    REF -->|mode: movie_release| DMR
    PI --> E([END])
```

- **`discover_generic_news`** / **`discover_movie_releases`**: raccolgono spunti (ricerca Tavily + estrazione strutturata), a seconda della modalità. I film in uscita vengono letti da un CSV locale (`data/movies.csv`), non più da Google Calendar.
- **`select_items`**: seleziona fino a `MAX_POSTS_PER_RUN` spunti, scartando quelli già trattati negli ultimi `HISTORY_WINDOW_DAYS` giorni (storico persistente in `data/history.json`).
- **`refine_query`**: se tutti gli spunti vengono scartati, un nodo LLM riformula la direzione di ricerca e si torna alla discovery (massimo `MAX_DISCOVERY_ATTEMPTS` tentativi totali).
- **`process_item`**: per ogni spunto selezionato (eseguito in parallelo via `Send`), approfondisce con una ricerca mirata, scrive il post, genera l'immagine (coerente con il template di brand in `data/brand_template.png`) e salva entrambi su disco.

## Setup

```bash
uv sync
cp .env.example .env
```

Compila `.env` con:
- `OPENAI_API_KEY` — usata per tutti gli LLM (testo) e per la generazione immagini (gpt-image-2)
- `TAVILY_API_KEY` — ricerca web ([tavily.com](https://tavily.com))

Serve anche:
- `data/movies.csv` — colonne `titolo,data_uscita,data_proiezione`
- `data/brand_template.png` — immagine di riferimento per stile/logo/palette dei post generati

## Uso

```bash
uv run social-media-manager-agent --mode generic_news
uv run social-media-manager-agent --mode movie_release
```

Output: un file `.json` per post in `output/posts/` e l'immagine corrispondente in `output/images/`.

## Configurazione

Tutti i parametri numerici/di comportamento sono in `.env`, nessun valore hardcoded nel codice:

| Variabile | Descrizione | Default |
|---|---|---|
| `DEFAULT_MODEL` | Modello OpenAI di default per tutti i nodi testuali | `gpt-4o-mini` |
| `MODEL_<NOME_NODO>` | Override modello per singolo nodo (es. `MODEL_WRITE_POST=gpt-4o`) | — |
| `MAX_POSTS_PER_RUN` | Numero massimo di post generati per esecuzione | `3` |
| `BROAD_SEARCH_RESULTS` | Risultati Tavily per la ricerca ampia (notizie generiche) | `10` |
| `MOVIE_SEARCH_RESULTS` | Risultati Tavily per la ricerca ampia per film | `6` |
| `FOCUSED_SEARCH_RESULTS` | Risultati Tavily per la ricerca di approfondimento | `4` |
| `HISTORY_WINDOW_DAYS` | Finestra (giorni) usata per evitare argomenti duplicati | `15` |
| `MAX_DISCOVERY_ATTEMPTS` | Tentativi massimi di discovery prima di arrendersi | `2` |
| `IMAGE_MODEL` | Modello per la generazione immagini | `gpt-image-2` |
| `IMAGE_SIZE` | Dimensione immagine generata | `1024x1024` |
| `IMAGE_QUALITY` | Qualità immagine generata | `low` |
| `SAVE_FOLDER` | Cartella JSON dei post | `./output/posts` |
| `IMAGES_FOLDER` | Cartella immagini generate | `./output/images` |
| `MOVIES_CSV_PATH` | Path del CSV film in uscita | `./data/movies.csv` |
| `BRAND_TEMPLATE_PATH` | Path dell'immagine di brand identity | `./data/brand_template.png` |
| `HISTORY_PATH` | Path dello storico post | `./data/history.json` |

## Test

```bash
uv run pytest tests/ -v
```

Tutti i test sono deterministici e non fanno chiamate di rete reali (LLM e ricerca sono mockati dove necessario, o testati come puro I/O su file temporanei).

## Limitazioni note

- Nessuna pubblicazione automatica sui social: l'output è JSON + immagine pronti, la pubblicazione è un passo futuro.
- La lista dei film in uscita è manuale (CSV), non sincronizzata con fonti esterne.
- `legacy_adk_reference/` contiene il prototipo originale su Google ADK/Gemini, mantenuto localmente come riferimento storico (escluso dal repo via `.gitignore`).
