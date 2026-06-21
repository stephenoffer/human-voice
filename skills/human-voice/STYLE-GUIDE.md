# Style Guide — Structure Worth Keeping

The skill removes AI tells. It must not flatten *purposeful* structure into a new
uniform signature in the process. Stripping every list, every heading, and every
bold term is its own machine tell — it trades one fingerprint for another
(principle 2). This guide names the structure to preserve.

## Keep

- **Headings that map the document.** A reader should be able to scan headings
  and know what's where. Keep them; just hold one case convention.
- **Lists that earn their place.** Genuinely parallel items — steps in a
  procedure, options being compared, a config reference — are clearer as a list
  than as prose. Keep those. The tell is the *bold-lead-in listicle* where every
  item is `- **Term:** sentence`, not the existence of bullets.
- **Code, commands, and config verbatim.** Never paraphrase code into prose.
  Keep fenced blocks, inline code, flags, and paths exactly.
- **Code-comment density that matches the surrounding code.** When editing code
  comments, match the file's existing density and idiom; don't strip comments to
  "sound less AI."
- **Callout tiers** (note / warning / danger) where a document already uses them
  consistently. They carry information about severity.
- **Tables** when the data is genuinely tabular. A comparison across three
  dimensions is a table, not six paragraphs.

## Cut or vary

- Bold scattered mid-sentence for emphasis (not on defined terms).
- A `---` horizontal rule between every section.
- Emoji in headings and bullets outside genuinely casual/social copy.
- Lists used to avoid writing connected prose — if the items aren't parallel,
  they're paragraphs.
- Uniform list shape across a whole document (every list a bold-lead-in triad).

## The test

Ask of any structure: *does this carry information a reader needs, or is it
decoration?* Keep the first. Cut or vary the second. When unsure, prefer prose
for argument and lists for genuinely enumerable things.
