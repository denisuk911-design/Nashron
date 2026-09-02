# Luminifera visual shell handoff

This archive is a visual handoff of the current Product UI. It contains no
Python Core, API implementation, tests, build output, database, or provider
credentials. The UI keeps its real bridge calls and shows honest loading,
empty, and error states when the API is unavailable.

## Entry point

Open `app.html` through a small local static server so the `/v3/*` asset paths
resolve. From this folder:

```text
python -m http.server 8080
```

Then open `http://127.0.0.1:8080/app.html`. The current shell is designed for
the Luminifera API; without an API it remains a visual shell with graceful
empty/error states and does not invent team or work data.

## Structure

- `app.html` - Product shell and screen composition: Auth, Home/Iris,
  Constellation, Work, Files, and Settings.
- `runtime-config.js` - runtime API base configuration surface.
- `v3/styles.css` - base layout, typography, navigation, surfaces, and global
  responsive behavior.
- `v3/refinement.css` - product scene refinements and screen states.
- `v3/team-scene-v40.css` and `v3/team-scene-v40.js` - Iris-centered
  constellation scene, adaptive orbit paths, dormant nodes, and motion flow.
- `v3/config.js` - background and Iris media configuration.
- `v3/assets/background.jpg` - Earth/space background.
- `v3/assets/iris.png` - Iris portrait media.
- `v3/assets/iris.png` is the currently configured Iris media. The archive
  contains only assets referenced by the current `v3/config.js`.
- `v3/bridge.js` - browser-to-API bridge used by the shell; it contains no
  backend implementation.
- `v3/app.js`, `auth-gate.js`, `i18n.js`, provider and admin UI scripts - the
  current screen behavior and local UI support.

No visual changes were made for this handoff task.
