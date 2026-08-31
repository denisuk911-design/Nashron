# Packaged V3 media gate

Build under test: `dist/Luminifera.exe`.

## Verified scenarios

- Normal packaged config loaded the configured background image (`2560px`) and Iris image (`1123px`).
- A packaged-page reload with `config.js` set to video entries created `VIDEO` elements for both background and Iris.
- The intentionally missing video resources emitted media errors and the loader replaced them with the configured poster images (`2560px` and `1123px`).
- Removing the test interception and reloading restored the normal image configuration.
- The media settings action `Перечитать config.js` now performs a real page reload.
- No Product UI composition or design was changed; global vertical scroll remained absent.

## Checks

- Targeted static/UI tests: PASS.
- Packaged image/video/fallback gate: PASS.
- No fake media data was added to the product configuration.
