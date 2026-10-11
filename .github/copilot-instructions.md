# Unraid Themer

An Unraid plugin providing themes, a theme builder and icon sets, distributed through the
Community Applications store. `beta` is the update channel, `main` carries stable.

## Stack
PHP and CSS inside the Unraid webgui, with `build.py` generating the plugin artefacts.
Themes live in `themes/`, the packaged plugin in `plugin/`.

## What a review needs to know
- This plugin injects CSS and markup into the Unraid webgui, which runs as root. Anything
  writing files outside the plugin's own directories, or shelling out, needs a very good
  reason.
- Community-submitted themes are untrusted input. The sanitiser is the boundary that
  keeps a submitted theme from becoming script execution in someone's admin UI.
- Users update in place from the store. A change to the plugin file format has to keep
  working for installations built by an older version.

## Conventions
Code, comments and commit messages in English. Public repository with users worldwide.
