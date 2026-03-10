# Chatbot evaluation

Evaluation of retrieval and answer quality for the Smart FAQ / chatbot pipeline. Uses heuristic metrics only (no Ragas dependency).

## Quick start

1. **Build eval sets** from feedback data (writes timestamped JSONL under `data/evals/`):

   ```bash
   python scripts/build_eval_sets.py
   ```

2. **Run evaluation** (reads latest gold/needs_review/ambiguous JSONL, writes a report):

   ```bash
   python scripts/run_eval.py
   ```

   Optional: pass the evals directory:

   ```bash
   python scripts/run_eval.py data/evals
   ```

3. **Reports** are written to:

   ```
   data/evals/report_{timestamp}.json
   ```

## Metrics

- **Retrieval (heuristic):** recall@1, recall@3, % with citations, avg retrieved per query. MRR is a placeholder (requires ground-truth relevant doc ids or Ragas).
- **Answer quality (heuristic):** avg answer length, % with citations, correct/needs_review/ambiguous rates from set composition. Groundedness and relevance are placeholders (require Ragas or LLM-as-judge).

For full recall@k, MRR, groundedness, and relevance you’d need labeled data or Ragas integration.

## Weekly RAG improvement workflow

Use the maintenance script to build eval sets, run metrics, and dump incorrect questions for review. Optionally re-index KB documents.

**Run (from project root):**

```bash
./scripts/weekly_rag_improve.sh
```

**Steps:**

1. **Build eval sets** — `python scripts/build_eval_sets.py`  
   Reads `chatbot_feedback`, writes timestamped `gold_*.jsonl`, `needs_review_*.jsonl`, `ambiguous_*.jsonl` under `data/evals/`.

2. **Run eval metrics** — `python scripts/run_eval.py`  
   Computes retrieval/answer heuristics over the latest sets, writes `data/evals/report_{timestamp}.json`.

3. **Dump top 50 incorrect for review** — `python scripts/dump_incorrect_for_review.py`  
   Uses the latest `needs_review_*.jsonl`, writes `data/evals/incorrect_for_review_{timestamp}.md` (table: question, answer snippet, rating, id).

4. **Optional re-index** — pass `--reindex` to call `POST /api/chatbot/knowledge/revectorize`.  
   Requires `API_URL` and `CHATBOT_API_KEY` (or `API_KEY`) in the environment.

**With re-index:**

```bash
API_URL=http://localhost:5000 CHATBOT_API_KEY=fik_xxx ./scripts/weekly_rag_improve.sh --reindex
```

**Env (optional):** `EVALS_DIR`, `LIMIT` (default 50), `API_URL`, `CHATBOT_API_KEY`/`API_KEY` for `--reindex`. Schedule via cron, e.g. `0 9 * * 1 cd /path/to/Fikiri && ./scripts/weekly_rag_improve.sh`.

## See also

- [CHATBOT_FEEDBACK_API.md](CHATBOT_FEEDBACK_API.md) — feedback API and storage
- [CHATBOT_EMBED.md](CHATBOT_EMBED.md) — embed and public endpoint
