# We rewrote the parser in Rust, and I would do it again

Our config parser was written in Python. It was correct, but slow. For a 40-megabyte YAML file it needed almost nine seconds, and customers with large fleets complained often. So in January we rewrote it in Rust.

I will be direct: the rewrite was painful. None of us knew Rust well. For two weeks the borrow checker fought me, and I wrote things in a way that a real Rust developer would laugh at. My first version used clone() everywhere just to make the compiler stop shouting.

But the result speaks. The same 40-megabyte file now parses in 340 milliseconds. Because we expose it to Python through PyO3, the rest of the system did not change at all, and the team kept their familiar API.

The honest cost is maintenance. We are five people, and now only two of us can comfortably touch the parser. That is a real risk, and I do not pretend it away. We are paying for training so the others can join.

For a hot path that runs millions of times a day, the trade was worth it. Had it been a script that runs once a week, I would have stayed in Python without a second thought.
