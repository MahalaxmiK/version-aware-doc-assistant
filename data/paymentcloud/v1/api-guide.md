# PaymentCloud API Guide

Product version: v1

## Authentication

PaymentCloud version 1 authenticates requests using secret API keys. Clients must send the key in the `X-Payment-Key` request header.

## Transaction limits

Version 1 permits transactions up to $5,000. Transactions exceeding this amount are rejected.

## Refunds

Version 1 supports full refunds only. Partial refunds are not available.