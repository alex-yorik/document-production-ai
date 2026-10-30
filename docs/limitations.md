# Limitations

This is a working prototype / demo (level D), not a production system. Current
limitations include:

- **Text-only issue resolution.** An issue counts as resolved also when it was
  rephrased or downgraded in severity; there is no semantic verification of the fix.
- **Retrieval is a matching-word counter** over chunks, not embeddings-based
  semantic search.
- **One LLM provider.** The pipeline uses DeepSeek only; there is no provider
  fallback.
- **No authentication or multi-user support.** The Streamlit UI is single-user
  and local.
- **Source-dependent quality.** Document quality depends on the quality of the
  supplied sources; the pipeline cannot compensate for missing or unreliable input.
- **Single demo sample.** The stored demo results are one run on one synthetic
  dataset, not a benchmark.
- **No compliance claim.** Using real data requires consent, a retention policy,
  and a review of local legislation; no regulatory compliance is claimed.
