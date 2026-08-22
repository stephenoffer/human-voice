# Choosing a vector store for retrieval

The decision comes down to how much operational surface you want to own. Managed services handle sharding and replication for you, but you pay per vector and you are bound to their query semantics. Self-hosting pgvector keeps everything in the database you already run, at the cost of tuning index parameters yourself and accepting that recall degrades once the index exceeds working memory.

For most teams under ten million vectors, pgvector is the right starting point. You already have backups, monitoring, and access control for Postgres. Adding a second stateful system is a real cost that tends to get underestimated during the prototype phase, when the dataset is small and everything is fast.

The case for a dedicated store gets stronger as filtering complexity grows. If your queries routinely combine vector similarity with several metadata predicates, the planner will often choose a sequential scan over the index, and latency becomes unpredictable. At that point the specialized engines earn their keep, because pre-filtering is designed into the index rather than bolted on.

One caveat worth naming: benchmarks published by vendors measure recall on datasets chosen to flatter their index. Run your own queries against your own embeddings before committing, and measure the tail rather than the mean.
