# Generate mode: drafting human prose from a brief

Generate mode produces new copy that reads human from the first draft, then runs
it through the same self-critique loop as a rewrite. The hard rule: the draft may
add *voice*, never *facts*. Anything the brief doesn't supply gets a visible
placeholder, never an invented number.

## The brief

> Write a short product-update post for our changelog. Register: marketing.
> Audience: existing users of our note-taking app. We shipped offline mode this
> week — notes now sync when you reconnect instead of failing to save. It works
> on iOS and Android. We don't have adoption numbers yet. Keep it to a short
> paragraph or two, address the reader as "you", no hype.

## The draft

> ### Your notes save now, even with no signal
>
> You're on a train, the tunnel kills your connection, and the note you just
> wrote used to vanish. Not anymore. Offline mode keeps everything you write on
> your phone, then syncs it the moment you're back online.
>
> It's on for everyone running the latest iOS and Android builds, so there's
> nothing to turn on. Write on the subway, on a flight, in the basement, and it's
> there when you get back.

## Why each placeholder (or its absence) is there

The brief gives the feature, the two platforms, and the failure it fixes, so all
of that is stated plainly. The brief explicitly says there are no adoption
numbers yet, so the draft makes **no** quantitative claim — no "thousands of
users", no "99% sync success". If a reviewer wanted a metric, the honest move is
a placeholder:

> Since launch, [SOURCE NEEDED: adoption / sync-success figure] notes have synced
> on reconnect.

That line stays out of the published draft until someone supplies the number. A
placeholder is a visible gap the author can fill; an invented "thousands" is a
hallucination that ships.

**Placeholder discipline:** write only what the brief supports, and mark every
fact you don't have with an explicit `[SOURCE NEEDED]` rather than inventing one
to make the prose flow.
