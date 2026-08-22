# Choosing a vector store for retrieval

Start with pgvector. Under about ten million vectors it wins, and the reason has
nothing to do with recall benchmarks: it is the database you already back up,
already monitor, already have access control for. A second stateful system is a cost that arrives
months after the prototype, when the dataset is small and every query is fast and
nobody is thinking about it.

What you give up is real. You tune HNSW parameters yourself. Recall falls off
once the index outgrows working memory, and it falls off quietly.

The argument flips on filtering. Combine vector similarity with several
metadata predicates and the planner starts choosing a sequential scan over the
index. Latency stops being a number you can quote. Dedicated engines design
pre-filtering into the index instead of bolting it on afterward, and that is
where they earn the operational cost.

Vendor benchmarks measure recall on datasets chosen to flatter the vendor's
index. Run your own embeddings through your own queries, watch the tail rather
than the mean, and decide from that.
