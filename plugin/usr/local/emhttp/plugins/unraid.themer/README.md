A generic theming plugin for the Unraid 7 webGUI. Pick a preset (or drop your own
CSS), toggle it on/off, and the whole UI restyles — classic Dynamix pages and the
new Vue web-components, via CSS custom properties.

Open **Settings → Utilities → Unraid Themer**.

Presets: bebamu (Light + Dark), Nord, Dracula, Solarized Dark, Monokai, Gruvbox Dark.
Custom CSS overrides load on top of the preset. Semantic status colors (disk health,
array state) are left untouched. Zero footprint when disabled.

Add your own preset by dropping `<name>.css` in
`/boot/config/plugins/unraid.themer/presets/`.
