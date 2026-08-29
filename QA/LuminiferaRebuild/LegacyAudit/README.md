# Legacy audit

Product Mode entry points now use the Luminifera shell, Home, Chat, Work, Files, Iris, Settings and owner Profile surfaces. The old dialogs and runtime services remain in the repository as compatibility fallbacks until a final audit confirms every required action has a replacement.

Known remaining migration surface:

- `gui/settings_dialog.py` remains an internal compatibility dialog but is no longer the Product Mode settings entry point;
- legacy director/management dialogs remain service-backed fallbacks;
- internal `Team2050` identifiers and executable filename are retained where migration would risk runtime behavior.
