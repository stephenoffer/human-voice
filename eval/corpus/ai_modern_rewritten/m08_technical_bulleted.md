# Reducing cold-start latency in serverless functions

Cold starts are the standard complaint about serverless, and the advice online
mostly treats symptoms. The actual problem is that your initialization cost gets
charged to a request some person is sitting there waiting on.

Four things drive it. The runtime downloads and extracts your bundle, so package
size shows up directly in the number. Interpreted runtimes start faster than
JVM-based ones, though ahead-of-time compilation has narrowed that. Opening a
database connection during init is common and expensive, especially once a TLS
handshake is involved. And functions that fetch secrets or feature flags at startup
have bought themselves a network round trip on every cold start.

The fix that pays is making that work lazy. A connection opened on first use costs
exactly what it cost before. It just lands on a warm invocation, usually, instead of
a cold one.

Provisioned concurrency solves the whole thing by keeping instances alive, and you
pay for that. Worth it on a user-facing path with predictable traffic. Almost never
worth it for background processing.
