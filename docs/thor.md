# GPcal on AYN Thor

This fork maintains the application in `gpcal/gamedata`, based on the upstream
`rocknix` branch. The Arch package is maintained directly in `packaging/arch`.
The upstream runtime archive supplies only the Pyxel dependency environment;
application files embedded inside it are never installed or rewritten.

## Calibration

Launch GPcal from the applications menu. Close games first: the launcher
temporarily stops InputPlumber so calibration can read the physical gamepad.
InputPlumber is restored when GPcal exits, including ordinary errors and handled
termination signals. A forced kill or power loss cannot run process cleanup.

The input reader identifies Thor and Retroid physical gamepads, detects supported
trigger axes from evdev capabilities and never silently calibrates a virtual SDL
controller. Both `ABS_Z` / `ABS_RZ` and older `ABS_HAT2X` / `ABS_HAT2Y` are supported.
The Thor `rsinput` and Retroid `retroid` parameter directories are discovered at
runtime. Device event numbers and the bundled Python runtime version are not fixed.

Use **Save** after calibration. Numeric settings are atomically stored in
`/var/lib/gpcal/calibration.json`, readable and writable by root. The system service
`thorch-gpcal-restore.service` restores settings before InputPlumber starts.
The InputPlumber drop-in pulls this service in automatically.

Existing `~/.config/autostart/GPcal.sh` data can be migrated with:

```sh
sudo thorch-gpcal-calibration import-legacy "$HOME/.config/autostart/GPcal.sh"
```

Only recognized numeric assignments are imported. The shell file is never
executed, and remains unchanged. When no new state exists, the launcher also
attempts this import from the invoking user's home directory.

`thorch-gpcal-calibration inspect` reads the live numeric configuration without
changing it. `restore` applies the saved configuration; do not run it while
calibration is in progress. No settings are invented if the state file is absent.

## Packaging

Build as an ordinary user from the checkout:

```sh
cd packaging/arch
makepkg --nodeps --force --ignorearch
```

The package is for aarch64. The existing Thorch browser-based gamepad tester
assets are retained unchanged to preserve the other entry point supplied by the
previous package. Those assets originate from Thorch's gamepad calibration payload.
The Thor fork is the maintenance location for this package; do not add source
replacement rules to the former Thorch packaging recipe.

Source: https://github.com/cdeletre/GPcal (upstream `rocknix` branch).
Fork: https://github.com/lurenjiamax/GPcal (`thor` branch).
