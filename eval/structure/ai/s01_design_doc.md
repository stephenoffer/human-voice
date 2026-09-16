# Event Ingestion Service: Design Document

## Overview

This document describes the design of the new event ingestion service. The service will replace the current batch-based pipeline with a streaming architecture that delivers events to downstream consumers in near real time. The goal is to reduce end-to-end latency, improve reliability, and make it easier for product teams to add new event types without coordinating with the data platform team.

The new service is designed to be scalable, reliable, and easy to operate. It will support the existing event schema while allowing new event types to be registered through a self-service workflow.

## Background

Today, events are collected by the web and mobile clients and written to object storage in hourly batches. A nightly job reads these files, validates them, and loads them into the warehouse. This approach worked well when the company had a small number of event types and few consumers, but it has become a bottleneck as the number of teams relying on event data has grown.

Product teams have repeatedly asked for fresher data. Several teams have built their own side pipelines to work around the delay, which has led to duplicated logic, inconsistent validation, and higher operational overhead for everyone involved.

## Goals

- Deliver events to downstream consumers within 60 seconds of ingestion.
- Allow product teams to register new event types without platform involvement.
- Provide consistent schema validation across all event sources.

## Non-Goals

- Replacing the warehouse or changing how analysts query event data.
- Supporting arbitrary transformations inside the ingestion path.
- Migrating historical data from the batch pipeline.

## Architecture

The service consists of three components: an ingestion API, a validation layer, and a delivery layer. Clients send events to the ingestion API over HTTPS. The API authenticates the request, assigns an event ID, and writes the raw payload to a Kafka topic partitioned by `tenant_id`. Each partition is replicated with `replication.factor=3` and `min.insync.replicas=2`, so a single broker failure does not lose acknowledged writes.

The validation layer is a set of stateless consumers running in the `ingest-validate` deployment. Each consumer reads from the raw topic, looks up the schema for the event type in the schema registry, and validates the payload against the registered Avro schema. Valid events are written to the `events.validated` topic; invalid events go to `events.dlq` with the validation error attached as a header. Consumers commit offsets only after the downstream write succeeds, which gives at-least-once delivery. Deduplication happens downstream using the event ID.

The delivery layer uses Kafka Connect with the S3 sink and the warehouse sink. The S3 sink flushes every 30 seconds or 50 MB, whichever comes first. The warehouse sink uses the Snowpipe Streaming API with a 10-second flush interval. In load tests at 40,000 events per second, p50 end-to-end latency was 14 seconds and p99 was 41 seconds.

## Scalability

The service is designed to scale horizontally as event volume grows. Each component can be scaled independently based on demand, which ensures that the system can handle increased load without degrading performance. This approach provides flexibility and allows the team to respond quickly to changes in traffic patterns.

As more product teams adopt the service, the architecture will continue to support growth without requiring significant changes. Scaling decisions will be guided by monitoring data and capacity planning, ensuring that resources are used efficiently while maintaining a high level of reliability for all consumers of event data.

## Security

All traffic is encrypted in transit.

## Monitoring

Dashboards and alerts will be set up for key metrics.

## Rollout Plan

Rollout will happen in phases.

## Summary

In summary, the new event ingestion service replaces the current batch-based pipeline with a streaming architecture that delivers events to downstream consumers in near real time. It reduces end-to-end latency, improves reliability, and makes it easier for product teams to add new event types without coordinating with the data platform team. The service is scalable, reliable, and easy to operate, and it supports the existing event schema while allowing new event types to be registered through self-service.
