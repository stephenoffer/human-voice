# Deploying a static site with automated builds

By the end of this you will have a site that rebuilds and republishes every
time you push to main. No server to log into.

You need a Git repository, a domain you control, an account with a static host,
and Node.js 18 or later. Some command-line comfort is assumed.

Start with the build. Add a script to `package.json` that writes static files
into `dist`. The important property is reproducibility: same input, same
output, no dependence on anything outside the repo.

Next, connect the repository in your host's dashboard and tell it the build
command and the output directory. It runs the build in a clean container. If
you have a dependency installed locally but never declared it, this is where
you find out.

Point a CNAME at the hostname your host gives you. DNS usually settles within
an hour, sometimes in five minutes, so do this before you need it.

Then push something small to main and read the build log. A good run ends with
an upload step and a deployment URL.

Two failures account for most first attempts. A missing dependency usually
means it landed in `devDependencies` instead of `dependencies`. Assets
returning 404 after a successful deploy almost always means the base path in
your build config is wrong.
