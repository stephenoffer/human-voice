# Payments Platform: Architecture Guide for New Engineers

## Welcome

Welcome to the payments platform team! This guide will help you understand how our systems fit together so you can start contributing quickly. It covers the main services, how money moves through them, and the design decisions that shape our work.

## How Money Moves

Every payment starts as a `PaymentIntent` created by the `intents` service. The intent records the amount in minor units, the currency, and an idempotency key supplied by the caller. Idempotency keys are stored for 24 hours in Redis, so a retried request returns the original intent rather than creating a second charge.

The `router` service picks a processor for each intent based on currency, card network, and the processor health scores published every 15 seconds. Authorization goes to the processor; the response is written to the `ledger` service as a pending entry before the API returns. Capture happens asynchronously when the merchant confirms fulfilment.

The `ledger` is double-entry and append-only. Every movement of money is two rows that sum to zero, and balances are derived, never stored. This means that any balance can be recomputed from history, which is how we reconcile against processor settlement files each night.

## Key Design Decisions

We made the ledger double-entry and append-only so that every movement of money is recorded as two rows that sum to zero and balances can always be recomputed from history. Idempotency keys are stored for 24 hours so a retried request returns the original intent rather than creating a second charge. The router picks a processor for each intent based on currency, card network, and processor health scores.

## Testing

Tests are important for maintaining quality.

## Deployment

We deploy regularly.

## Summary

To summarize, every payment starts as a PaymentIntent with an idempotency key stored for 24 hours so retried requests return the original intent. The router picks a processor based on currency, card network, and health scores. The ledger is double-entry and append-only, so every movement of money is two rows summing to zero and balances can be recomputed from history. Welcome aboard!
