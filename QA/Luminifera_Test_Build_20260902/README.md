# Luminifera visual shell integration test build

Run `Luminifera-Test.exe` on Windows. This package contains the packaged V3
product shell with the lead visual layer integrated on top of the existing
Core/API/runtime.

The executable is a local owner-test artifact and is intentionally kept out of
the source commit because it is larger than GitHub's regular file limit.

Verified separately:

- packaged signup, Iris chat, route switch, reload, logout/login persistence;
- wheel scrolling does not change the active route;
- JavaScript syntax and Python compilation;
- web shell was rebuilt from current source.
