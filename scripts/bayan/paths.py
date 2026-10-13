"""Reading path validation (docs/09-reading-path-framework.md)."""

from __future__ import annotations

from .common import Report, rel
from .metadata import Library

# Level -> (minimum works, maximum works or None)
LEVEL_SIZES = {
    "Beginner": (5, 15),
    "Intermediate": (10, 25),
    "Scholar": (20, None),
}


def prerequisite_pairs(lib: Library) -> set[tuple[str, str]]:
    pairs = set()
    for edge in lib.relationships:
        if edge.get("relationship") == "prerequisite_of":
            pairs.add((edge.get("source"), edge.get("target")))
        elif edge.get("relationship") == "requires":
            pairs.add((edge.get("target"), edge.get("source")))
    return pairs


def run(lib: Library) -> Report:
    report = Report("Reading path validation")
    prerequisites = prerequisite_pairs(lib)
    for path in lib.by_type("reading_path"):
        where = f"{rel(path.path, lib.root)}#{path.id}"
        books = path.data.get("included_books") or []
        level = path.data.get("level")
        for book in books:
            if book not in lib.records:
                report.add("critical", "missing-work",
                           f"{book} has no metadata record", where)
        duplicates = sorted({b for b in books if books.count(b) > 1})
        for book in duplicates:
            report.add("major", "duplicate-work",
                       f"{book} appears more than once", where)
        if level in LEVEL_SIZES:
            low, high = LEVEL_SIZES[level]
            if len(books) < low or (high is not None and len(books) > high):
                span = f"{low}-{high}" if high else f"{low}+"
                report.add("major", "path-size",
                           f"{level} paths hold {span} works, this one "
                           f"holds {len(books)}", where)
        estimated = path.data.get("estimated_books")
        if estimated is not None and estimated != len(books):
            report.add("minor", "estimated-books",
                       f"estimated_books is {estimated}, list has "
                       f"{len(books)}", where)
        position = {book: i for i, book in enumerate(books)}
        for before, after in sorted(prerequisites):
            if before in position and after in position and \
                    position[before] > position[after]:
                report.add("major", "prerequisite-order",
                           f"{before} is a prerequisite of {after} but "
                           "comes later in the path", where)
        if not path.data.get("outcomes"):
            report.add("minor", "outcomes",
                       "paths should state learning outcomes", where)
    return report
