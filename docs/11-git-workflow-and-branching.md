# Git Workflow and Branching

## Purpose

This document defines the Git workflow, branching strategy, merge rules, release
process, and repository maintenance practices for The Bayan Library.

The objective is to ensure repository stability while supporting continuous
growth, experimentation, and contribution.

A consistent workflow reduces risk, improves quality, and simplifies long-term
maintenance.

## Workflow Principles

The repository workflow should:

- Protect the main branch.
- Encourage incremental changes.
- Support peer review.
- Maintain traceability.
- Enable safe experimentation.
- Improve collaboration.

Every substantive change should be traceable from proposal to merge.

## Branching Strategy

The Bayan Library follows a modified Git Flow model.

The primary branches are:

```text
main
develop
```

Supporting branches are:

```text
feature/*
research/*
docs/*
refactor/*
automation/*
fix/*
release/*
```

Each branch type has a specific purpose.

## Main Branch

The `main` branch represents the production state of the repository.

Requirements:

- Stable content only.
- Reviewed content only.
- No direct commits.
- Release-ready state.

The main branch should always remain usable and well documented.

## Develop Branch

The `develop` branch serves as the integration branch.

Purpose:

- Consolidate approved changes.
- Validate compatibility across updates.
- Prepare future releases.

Most pull requests should target `develop` first.

## Feature Branches

Feature branches are used for new content.

Naming convention:

```text
feature/add-book-war-and-peace

feature/add-author-ibn-sina

feature/add-reading-path-world-poetry

feature/add-islamic-canon
```

Feature branches should focus on a single logical improvement.

## Documentation Branches

Documentation branches are used for repository documentation.

Naming convention:

```text
docs/update-readme

docs/improve-specification

docs/add-contribution-guide
```

Documentation improvements should be isolated from unrelated work.

## Research Branches

Research branches support exploratory work.

Naming convention:

```text
research/islamic-intellectual-history

research/world-poetry-ranking

research-top-500-candidates
```

Research branches may contain incomplete work.

They should not be merged until validated.

## Refactor Branches

Refactor branches improve repository structure without changing content meaning.

Naming convention:

```text
refactor/metadata-schema

refactor/index-generation

refactor-directory-structure
```

Refactors should avoid introducing unnecessary changes.

## Automation Branches

Automation branches improve repository tooling.

Naming convention:

```text
automation/build-index

automation/knowledge-graph

automation/link-validation
```

Automation changes should include testing where practical.

## Fix Branches

Fix branches resolve problems.

Naming convention:

```text
fix/broken-links

fix/metadata-errors

fix/duplicate-identifiers
```

Fixes should be narrowly scoped.

## Release Branches

Release branches prepare official releases.

Naming convention:

```text
release/v1.0.0

release/v1.1.0

release/v2.0.0
```

Release branches should focus on stabilization and validation.

## Branch Protection Rules

The following rules should protect production branches:

For `main`:

- No direct commits.
- Pull request required.
- Status checks required.
- Review required.

For `develop`:

- Pull request preferred.
- Validation checks required.

Branch protection helps preserve repository integrity.

## Commit Standards

All commits should follow Conventional Commits.

Examples:

```text
feat(book): add muqaddimah summary

feat(author): add mulla sadra profile

feat(poetry): add hafez collection

docs(spec): expand metadata requirements

fix(links): repair broken canon references

refactor(metadata): normalize author records

chore(index): regenerate master catalog
```

Commit messages should clearly communicate intent.

## Commit Guidelines

Each commit should:

- Address one logical change.
- Be self-contained.
- Be understandable without additional explanation.

Avoid large unrelated commits.

## Atomic Commit Principle

Commits should be atomic.

Good example:

```text
feat(author): add ibn khaldun profile
```

Poor example:

```text
updated many files
```

Atomic commits simplify review and troubleshooting.

## Pull Request Workflow

Recommended workflow:

```text
Create Branch
↓
Make Changes
↓
Validate Changes
↓
Commit Changes
↓
Open Pull Request
↓
Review
↓
Revise
↓
Merge
```

This workflow should be followed for most repository updates.

## Pull Request Requirements

Every pull request should include:

- Summary
- Purpose
- Files changed
- Knowledge impact
- Future opportunities

The repository pull request template should be used whenever available.

## Pull Request Size Guidelines

Preferred pull requests should be:

- Focused
- Reviewable
- Well documented

Large pull requests should be divided into smaller logical units whenever
possible.

## Review Requirements

Reviewers should evaluate:

- Accuracy
- Consistency
- Metadata quality
- Cross-link quality
- Documentation quality
- Repository alignment

Reviews should focus on improving quality rather than merely approving changes.

## Merge Strategy

Preferred merge strategy:

```text
Squash and Merge
```

Benefits include:

- Cleaner history
- Reduced noise
- Easier auditing

Exceptions may be made for large development efforts.

## Conflict Resolution

When merge conflicts occur:

1. Review both versions.
2. Preserve valuable information.
3. Resolve inconsistencies.
4. Revalidate links and metadata.

Conflict resolution should prioritize repository quality.

## Release Workflow

Recommended release workflow:

```text
Develop
↓
Release Branch
↓
Validation
↓
Documentation Review
↓
Version Tag
↓
Main Branch
```

Releases should represent stable repository milestones.

## Semantic Versioning

The repository follows semantic versioning.

Format:

```text
MAJOR.MINOR.PATCH
```

Examples:

```text
1.0.0
1.2.0
2.0.0
```

Version meaning should remain consistent.

## Major Releases

Major releases indicate significant changes.

Examples:

- Governance updates.
- Architecture redesigns.
- Major canon revisions.
- Structural migrations.

Major releases may introduce breaking changes.

## Minor Releases

Minor releases indicate substantial enhancements.

Examples:

- New canons.
- New reading paths.
- New metadata capabilities.
- Significant content expansion.

Minor releases should remain backward compatible.

## Patch Releases

Patch releases indicate maintenance work.

Examples:

- Typographical corrections.
- Metadata repairs.
- Broken link fixes.
- Documentation clarification.

Patch releases should not alter repository behavior significantly.

## Tagging Strategy

Every release should be tagged.

Examples:

```text
v1.0.0

v1.1.0

v2.0.0
```

Tags support repository history and reproducibility.

## Changelog Requirements

Each release should include a changelog.

Suggested sections:

```text
Added

Changed

Fixed

Removed

Future Work
```

Changelogs improve transparency and historical traceability.

## Continuous Improvement

Workflow rules may evolve as the repository grows.

Changes should:

- Be documented.
- Be justified.
- Improve maintainability.
- Preserve consistency.

Significant workflow changes should be reviewed carefully.

## Automation Integration

The workflow should integrate with:

- Link validation
- Metadata validation
- Index generation
- Knowledge graph generation
- Documentation checks

Automation should support human contributors rather than replace them.

## AI Contribution Requirements

AI-generated content should:

- Follow repository templates.
- Include metadata.
- Respect formatting standards.
- Support cross-linking.
- Remain reviewable by humans.

AI assistance should improve productivity while maintaining quality.

## Success Criteria

The Git workflow succeeds when it:

- Protects repository quality.
- Enables contribution.
- Improves traceability.
- Supports automation.
- Maintains stability.
- Scales with repository growth.

The workflow should become more valuable as the repository expands.

## Workflow Summary

The Git workflow and branching model provide the operational foundation for
maintaining The Bayan Library.

A disciplined workflow ensures that books, notes, metadata, canons, reading
paths, and knowledge graphs can grow continuously while remaining organized,
reliable, and maintainable.
