# Retro: the Q2 redesign launch

We shipped the redesign three weeks late. Not a disaster, but worth understanding why, because we keep doing this.

The honest answer is we underestimated the migration. Everyone focused on the new front end, which looked great in Figma and demoed well. Nobody owned the part where 60,000 existing user preferences had to map onto the new settings schema. Priya found the gap two days before launch and basically rebuilt the migration script over a weekend, which is heroic and also exactly the thing we don't want to depend on.

What went well: the feature flag rollout. We turned it on for 5% of users first, caught a layout bug on Safari, and fixed it before anyone else saw it. That process worked and we should keep it.

What I'd change: someone needs to own data migration as a real task, not a footnote. I'm going to add it as a required checklist item on every launch ticket. It's boring. That's the point. The boring stuff is what bit us.
