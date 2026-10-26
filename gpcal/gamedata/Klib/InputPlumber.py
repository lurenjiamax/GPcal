"""Owned InputPlumber raw-calibration transport, with an evdev-compatible reader."""
import time

import dbus
from evdev import AbsInfo, InputEvent, ecodes

SERVICE = 'org.shadowblip.InputPlumber'
ROOT = '/org/shadowblip/InputPlumber'
INTERFACE = 'org.shadowblip.Input.Source.EventDevice'


class CalibrationDevice:
    def __init__(self, bus, path, name):
        self.bus = bus
        self.path = str(path)
        self.name = str(name)
        self.interface = dbus.Interface(bus.get_object(SERVICE, path), INTERFACE)
        self.closed = True
        self.axes = {}
        self.pending = []
        self.interface.BeginCalibration()
        self.closed = False
        try:
            self.refresh()
        except Exception:
            self.close()
            raise

    def _receive(self):
        ready, overflow, axes, events = self.interface.ReadCalibration()
        if overflow:
            raise RuntimeError('Raw calibration event queue overflowed; repeat the calibration step')
        self.axes = {int(code): AbsInfo(*(int(value) for value in info))
                     for code, *info in axes}
        self.pending.extend(InputEvent(0, 0, int(kind), int(code), int(value))
                            for kind, code, value in events)
        return bool(ready)

    def refresh(self):
        self.interface.RefreshCalibration()
        deadline = time.monotonic() + 5
        while not self._receive():
            if time.monotonic() >= deadline:
                raise RuntimeError('InputPlumber calibration source did not become ready')
            time.sleep(.01)

    def absinfo(self, code):
        return self.axes[code]

    def read(self):
        self._receive()
        events, self.pending = self.pending, []
        return events

    def close(self):
        if not self.closed:
            try:
                self.interface.EndCalibration()
            finally:
                self.closed = True
                self.bus.close()


def open_calibration(names):
    bus = dbus.SystemBus(private=True)
    if not bus.name_has_owner(SERVICE):
        bus.close()
        return None
    try:
        manager = dbus.Interface(bus.get_object(SERVICE, ROOT), 'org.freedesktop.DBus.ObjectManager')
        objects = manager.GetManagedObjects()
        for path, interfaces in objects.items():
            properties = interfaces.get(INTERFACE, {})
            if str(properties.get('Name', '')) not in names:
                continue
            axes = {int(code) for code in properties.get('SupportedAbsoluteAxes', [])}
            required = {ecodes.ABS_X, ecodes.ABS_Y, ecodes.ABS_RX, ecodes.ABS_RY}
            if not required <= axes:
                continue
            for triggers in ((ecodes.ABS_Z, ecodes.ABS_RZ),
                             (ecodes.ABS_HAT2X, ecodes.ABS_HAT2Y)):
                if set(triggers) <= axes:
                    return CalibrationDevice(bus, path, properties['Name']), triggers
        raise RuntimeError('InputPlumber has no supported physical calibration source')
    except Exception:
        bus.close()
        raise
