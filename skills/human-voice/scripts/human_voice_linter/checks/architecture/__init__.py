"""architecture — what a document spends its words on.

Every other check in the linter reads a sentence, a paragraph, or the markdown
shape. None of them reads the document as a plan: which points it makes, how many
times it makes them, how the words are shared out between sections, and whether
every section is written for the same reader. That is where an agent-written
report gives itself away after the diction and the syntax are clean. It says the
same thing in the overview, the body and the summary. It spends four hundred words
on the easy section and one sentence on the hard one. It explains what an API is
two sections after quoting a p99 at a reader it assumed was an expert.

Three checks, all of them count-gated, because every construction measured here is
also something a careful person does once:

- `restatement`: the same point made twice in different places.
- `section_balance`: stub sections next to a bloated one, sections so even they
  were plainly budgeted, framing sections that outweigh the substance, and every
  list cut to the same length.
- `depth_drift`: a long section with nothing checkable in it beside sections dense
  with specifics, or beginner explanations inside a document written for experts.

Judgment still does most of this work. A paraphrase that shares no words with the
sentence it repeats is invisible to a lexical comparison, and whether a section
deserves its length depends on what the reader needs. The checks are a floor.

    vocabulary   title and body patterns (framing, boilerplate, depth markers)
    sections     the Section model, built once per document; SectionCheck base
    restatement  RestatementCheck
    balance      SectionBalanceCheck
    depth        DepthDriftCheck
"""
from __future__ import annotations

from .balance import SectionBalanceCheck
from .depth import DepthDriftCheck
from .restatement import RestatementCheck
from .sections import Section, SectionCheck, document_sections, section_model

ARCHITECTURE_CHECKS = (
    RestatementCheck(),
    SectionBalanceCheck(),
    DepthDriftCheck(),
)

__all__ = [
    "Section",
    "SectionCheck",
    "document_sections",
    "section_model",
    "RestatementCheck",
    "SectionBalanceCheck",
    "DepthDriftCheck",
    "ARCHITECTURE_CHECKS",
]
