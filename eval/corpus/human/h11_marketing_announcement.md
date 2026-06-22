# Offline mode is here, finally

You asked for this more than anything else, and it took us longer than we'd like to admit. Starting today, the app works on the subway.

Here's what changed under the hood. We used to assume a connection for every action, so a flaky signal meant a spinner and a lost edit. Now your changes write to the device first and sync when you're back online. Open a document in a tunnel, edit it, close the laptop. It's there when you reconnect, merged cleanly unless two people touched the same paragraph, in which case we show you both and let you pick.

This is live for everyone on the desktop app right now. Mobile lands next month. If you hit a sync conflict that looks wrong, send it to us with the document ID and we'll dig in personally.
