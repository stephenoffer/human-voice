# Deploying a static site with automated builds

This guide walks you through setting up a static site with builds that run
automatically whenever you push to your main branch. By the end you will have a
working deployment pipeline, allowing you to publish changes without touching a
server.

## Prerequisites

You will need a Git repository, a domain you control, and an account with a
static hosting provider. This guide assumes you are comfortable with the command
line and have Node.js 18 or later installed.

## Step 1: Prepare your build

Add a build script to your `package.json` that outputs static files to a `dist`
directory. What matters here is that the build is reproducible, meaning it
produces the same output given the same input and does not depend on anything
outside the repository.

## Step 2: Connect the repository

In your hosting provider's dashboard, connect the repository and specify the
build command and output directory. The provider will run the build in a clean
container, ensuring that a dependency you have installed locally but not
declared will surface as a failure rather than silently working.

## Step 3: Configure the domain

Point a CNAME record at the hostname your provider gives you. DNS propagation
typically takes between five minutes and an hour, so it is worth setting this up
before you need it.

## Step 4: Verify the pipeline

Push a small change to your main branch and watch the build log. A successful
build ends with an upload step and a deployment URL, giving you confirmation
that the whole chain works.

## Troubleshooting

If the build fails with a missing dependency, check that it is in
`dependencies` rather than `devDependencies`. If the site deploys but assets
return 404, the most likely cause is an incorrect base path in your build
configuration.
