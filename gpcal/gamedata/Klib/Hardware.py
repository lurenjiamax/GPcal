"""Physical evdev input shared by Thor and Retroid calibration."""
import os
from pathlib import Path
from evdev import InputDevice, ecodes, list_devices


def parameters_directory():
    override=os.environ.get('GPCAL_PARAMETERS_DIR')
    if override:
        return Path(override)
    for module in ('rsinput','retroid'):
        path=Path('/sys/module')/module/'parameters'
        if path.is_dir(): return path
    return Path('/sys/module/retroid/parameters')


def open_gamepad():
    names={'AYN Odin2 Gamepad','Retroid Pocket Gamepad'}
    from Klib.InputPlumber import open_calibration
    session = open_calibration(names)
    if session is not None:
        device, triggers = session
        print(f'GPcal calibration session: {device.name} ({device.path})', flush=True)
        return device, triggers
    required={ecodes.ABS_X,ecodes.ABS_Y,ecodes.ABS_RX,ecodes.ABS_RY}
    for path in list_devices():
        device=InputDevice(path)
        axes={code for code,_ in device.capabilities().get(ecodes.EV_ABS,[])}
        if device.name in names and required<=axes:
            if {ecodes.ABS_Z,ecodes.ABS_RZ}<=axes:
                triggers=(ecodes.ABS_Z,ecodes.ABS_RZ)
            elif {ecodes.ABS_HAT2X,ecodes.ABS_HAT2Y}<=axes:
                triggers=(ecodes.ABS_HAT2X,ecodes.ABS_HAT2Y)
            else:
                device.close(); continue
            print(f'GPcal physical input: {device.name} ({path}); trigger axes {triggers}',flush=True)
            return device,triggers
        device.close()
    raise RuntimeError('Physical calibration gamepad is unavailable. Launch GPcal with its InputPlumber-aware launcher.')
