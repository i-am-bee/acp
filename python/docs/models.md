# Models

<!-- TOC -->
## Table of Contents
- [Models](#models)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Core](#core)
  - [Schemas](#schemas)
  - [Errors](#errors)
<!-- /TOC -->

---

## Overview

The models module provides `pydantic` models describing ACP data structures.

> [!NOTE]
>
> Location within the sdk: [models](/python/src/acp_sdk/models)

## Core

Core models are used directly by the SDK consumers. They describe ACP structures like `Message`, `MessagePart` or `Run`. 

> [!NOTE]
>
> Location within the sdk: [models.models](/python/src/acp_sdk/models/models.py)

## Schemas

Schema models are used by client and server implementations. They describe payloads of HTTP requests and responses.

> [!NOTE]
>
> Location within the sdk: [models.schemas](/python/src/acp_sdk/models/schemas.py)

## Errors

Error model describes errors within the system. SDK consumers can encounter errors in various places, during a stream, as part of the `Run` model or raised inside the `ACPError` exception.

> [!NOTE]
>
> Location within the sdk: [models.errors](/python/src/acp_sdk/models/errors.py)