# Metadata Schema

## Purpose

The Metadata Schema defines how structured information is stored, validated,
indexed, and maintained throughout The Bayan Library.

Metadata serves as the foundation of repository organization, searchability,
automation, analytics, reading-path generation, and knowledge graph
construction.

Every major repository object should have consistent metadata.

## Goals

The metadata system should:

- Improve discoverability.
- Support automation.
- Enable filtering and search.
- Support knowledge graph generation.
- Maintain consistency across the repository.
- Minimize duplication.
- Support future expansion.

Metadata should be human-readable and machine-readable.

## Design Principles

The metadata system should follow these principles:

- Consistency
- Simplicity
- Extensibility
- Interoperability
- Validation
- Reusability

Schema changes should remain backward compatible whenever practical.

## Metadata Storage Layers

Metadata may be stored in:

- Front matter
- YAML files
- CSV catalogs
- Bibliographic databases
- Knowledge graph relationship files

Structured data should remain synchronized.

## Core Metadata Objects

The repository manages metadata for:

- Books
- Authors
- Poets
- Civilizations
- Themes
- Quotations
- Reading paths
- Canons
- Notes
- Study guides

Each object type should have a defined schema.

## Directory Structure

```text
metadata/

├── books.yaml
├── authors.yaml
├── poets.yaml
├── civilizations.yaml
├── themes.yaml
├── quotations.yaml
├── reading-paths.yaml
├── canons.yaml
├── relationships.yaml
├── bibliography.bib
├── catalog.csv
└── index.yaml
```

## Book Metadata Schema

Every major book should contain metadata.

Example:

```yaml
id: book-war-and-peace
title: War and Peace
author_id: author-leo-tolstoy
publication_year: 1869
language: Russian
civilization: Europe
genre:
  - Novel
  - Historical Fiction
themes:
  - War
  - Society
  - Leadership
canon_memberships:
  - top-100-books
  - world-literature
related_books:
  - book-anna-karenina
  - book-the-brothers-karamazov
```

Book identifiers should remain stable.

## Required Book Fields

Required fields:

- id
- title
- author_id
- publication_year
- language
- civilization
- genre

Optional fields:

- translator
- isbn
- themes
- canon_memberships
- related_books
- tags
- references

## Author Metadata Schema

Example:

```yaml
id: author-ibn-sina
name: Ibn Sina
birth_year: 980
death_year: 1037
civilization: Islamic Civilization
region: Persia
disciplines:
  - Philosophy
  - Medicine
  - Logic
major_works:
  - book-canon-of-medicine
  - book-book-of-healing
influenced_by:
  - author-al-farabi
influenced:
  - author-suhrawardi
```

Author profiles should form a significant component of the repository knowledge
graph.

## Required Author Fields

Required fields:

- id
- name
- civilization
- disciplines

Optional fields:

- birth_year
- death_year
- region
- major_works
- influenced_by
- influenced
- related_thinkers

## Poet Metadata Schema

Example:

```yaml
id: poet-rumi
name: Jalal al-Din Rumi
birth_year: 1207
death_year: 1273
language: Persian
civilization: Islamic Civilization
major_works:
  - Masnavi
themes:
  - Love
  - Spirituality
  - Divine Union
related_poets:
  - poet-hafez
  - poet-attar
```

Poets may share schema elements with authors but should maintain poetry-specific
fields.

## Civilization Metadata Schema

Example:

```yaml
id: civilization-persia
name: Persia
period_start: -550
period_end: null
major_figures:
  - Ibn Sina
  - Ferdowsi
  - Hafez
major_themes:
  - Philosophy
  - Poetry
  - Mysticism
```

Civilizations serve as high-level organizational entities.

## Theme Metadata Schema

Example:

```yaml
id: theme-justice
name: Justice
description: Concepts of justice across traditions
related_themes:
  - Ethics
  - Law
  - Governance
```

Themes support cross-disciplinary navigation.

## Reading Path Metadata Schema

Example:

```yaml
id: path-islamic-philosophy
title: Islamic Philosophy
level: Intermediate
estimated_books: 12
included_books:
  - book-virtuous-city
  - book-book-of-healing
  - book-asfar
```

Reading paths should be machine-readable.

## Canon Metadata Schema

Example:

```yaml
id: canon-top-100-books
title: Top 100 Greatest Books Ever Written
methodology: global-canon-methodology
last_updated: 2026-10-13
```

Canons should maintain version history.

## Quotation Metadata Schema

Example:

```yaml
id: quote-rumi-001
author: Rumi
source: Masnavi
theme:
  - Spirituality
  - Wisdom
language: Persian
```

Every quotation should be traceable to its source.

## Relationship Schema

Relationships power the knowledge graph.

Example:

```yaml
source: author-al-farabi
relationship: influenced
target: author-ibn-sina
```

Controlled relationship vocabularies should be preferred.

## Relationship Types

Supported relationship types include:

- influenced
- studied
- taught
- translated
- inspired
- critiqued
- collaborated
- related_to

New relationship types should be documented before adoption.

## Tagging System

Tags should be standardized.

Examples:

- wisdom
- ethics
- leadership
- spirituality
- justice
- civilization
- politics
- theology
- science
- poetry

Avoid duplicate tags with different spellings.

## Naming Conventions

Identifiers should:

- Use lowercase letters.
- Use hyphens instead of spaces.
- Remain stable over time.

Examples:

```text
author-ibn-sina
book-war-and-peace
theme-spirituality
canon-top-100-books
```

Identifiers should never be reused.

## Data Validation Rules

All metadata files should pass validation.

Validation checks should include:

- Unique identifiers.
- Required field presence.
- Valid relationships.
- Valid references.
- Correct formatting.

Invalid metadata should fail automated checks.

## Schema Evolution

Metadata schemas may evolve.

Changes should:

- Preserve compatibility.
- Include migration guidance.
- Document rationale.
- Update validation scripts.

Breaking changes should be minimized.

## Index Generation

Indexes should be generated using metadata.

Examples:

- Author indexes
- Civilization indexes
- Canon indexes
- Theme indexes
- Timeline indexes

Automation should reduce manual maintenance.

## Search Optimization

Metadata should allow filtering by:

- Author
- Civilization
- Language
- Theme
- Time period
- Genre
- Canon membership

Searchability is a primary design objective.

## Knowledge Graph Integration

Metadata is the foundation of the knowledge graph.

Relationships should connect:

- Authors to works
- Works to themes
- Authors to influences
- Civilizations to figures
- Reading paths to works

All major repository entities should be graph-compatible.

## Bibliographic Data

Formal bibliographic information should be maintained in:

```text
metadata/bibliography.bib
```

Where available, records should include:

- Author
- Title
- Publisher
- Publication date
- Edition
- ISBN

Bibliographic data should support future citation systems.

## Success Criteria

The metadata system succeeds when it:

- Supports automation.
- Remains internally consistent.
- Enables discovery.
- Powers knowledge graphs.
- Simplifies maintenance.
- Scales with repository growth.

The metadata layer should become more useful as the repository expands.

## Metadata Summary

The Metadata Schema serves as the structural backbone of The Bayan Library.

It transforms a collection of files into an interconnected knowledge system that
supports discovery, learning, research, automation, and long-term intellectual
preservation.
