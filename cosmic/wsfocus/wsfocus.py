#!/usr/bin/env python3
"""Alternate focus between windows of the current COSMIC workspace.

Like GlazeWM's alt+space: jumps to the window used before the current one
(e.g. a floating window and the tiled one behind it), never leaving the
workspace. COSMIC always draws floating windows above tiled ones, so when
leaving a floating window that covers the target, it gets minimized, and
restored when switching back to it. With --list, only prints
the windows it sees.
"""
import os
import select
import struct
import sys
import time

from pywayland.client import Display

from gen.wayland import WlOutput, WlSeat
from gen.ext_foreign_toplevel_list_v1 import ExtForeignToplevelListV1
from gen.cosmic_toplevel_info_unstable_v1 import ZcosmicToplevelInfoV1
from gen.cosmic_toplevel_management_unstable_v1 import ZcosmicToplevelManagerV1
from gen.ext_workspace_v1 import ExtWorkspaceManagerV1

STATE_MINIMIZED = 1
STATE_ACTIVATED = 2
WS_ACTIVE = 1

STATE_FILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "wsfocus-last")


class Window:
    def __init__(self, ext):
        self.ext = ext
        self.cosmic = None
        self.id = None
        self.title = ""
        self.app_id = ""
        self.states = set()
        self.workspaces = set()
        self.geometry = None

    def area(self):
        return self.geometry[2] * self.geometry[3] if self.geometry else 0

    def overlaps(self, other):
        if not self.geometry or not other.geometry:
            return False
        ax, ay, aw, ah = self.geometry
        bx, by, bw, bh = other.geometry
        return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def main():
    display = Display()
    display.connect()
    registry = display.get_registry()
    g = {}

    outputs = []

    def on_global(reg, name, iface, version):
        # Window geometry is only reported relative to outputs we have bound.
        if iface == WlOutput.name:
            outputs.append(reg.bind(name, WlOutput, min(version, 4)))
        for cls, want in (
            (WlSeat, 1),
            (ExtForeignToplevelListV1, 1),
            (ZcosmicToplevelInfoV1, 3),
            (ZcosmicToplevelManagerV1, 1),
            (ExtWorkspaceManagerV1, 1),
        ):
            if iface == cls.name and iface not in g:
                g[iface] = reg.bind(name, cls, min(version, want))

    registry.dispatcher["global"] = on_global
    display.roundtrip()

    missing = [c.name for c in (WlSeat, ExtForeignToplevelListV1, ZcosmicToplevelInfoV1,
                                ZcosmicToplevelManagerV1, ExtWorkspaceManagerV1) if c.name not in g]
    if missing:
        sys.exit(f"compositor lacks: {', '.join(missing)}")

    windows = []
    active_ws = set()

    def on_workspace(mgr, ws):
        def on_state(h, state):
            if state & WS_ACTIVE:
                active_ws.add(h)
            else:
                active_ws.discard(h)
        ws.dispatcher["state"] = on_state

    g[ExtWorkspaceManagerV1.name].dispatcher["workspace"] = on_workspace

    def on_toplevel(lst, ext):
        w = Window(ext)
        windows.append(w)
        ext.dispatcher["identifier"] = lambda h, v: setattr(w, "id", v)
        ext.dispatcher["title"] = lambda h, v: setattr(w, "title", v)
        ext.dispatcher["app_id"] = lambda h, v: setattr(w, "app_id", v)
        w.cosmic = g[ZcosmicToplevelInfoV1.name].get_cosmic_toplevel(ext)

        def on_state(h, arr):
            data = bytes(arr)
            w.states = set(struct.unpack(f"{len(data) // 4}I", data))
        w.cosmic.dispatcher["state"] = on_state
        w.cosmic.dispatcher["ext_workspace_enter"] = lambda h, ws: w.workspaces.add(ws)
        w.cosmic.dispatcher["ext_workspace_leave"] = lambda h, ws: w.workspaces.discard(ws)
        w.cosmic.dispatcher["geometry"] = (
            lambda h, output, x, y, width, height: setattr(w, "geometry", (x, y, width, height)))

    g[ExtForeignToplevelListV1.name].dispatcher["toplevel"] = on_toplevel
    display.roundtrip()

    # cosmic-comp sends the per-window state on its next refresh, then "done".
    info_done = []
    g[ZcosmicToplevelInfoV1.name].dispatcher["done"] = lambda h: info_done.append(True)
    deadline = time.monotonic() + 1.0
    while not info_done and windows:
        left = deadline - time.monotonic()
        if left <= 0:
            break
        display.flush()
        if select.select([display.get_fd()], [], [], left)[0]:
            display.dispatch(block=True)

    current = next((w for w in windows if STATE_ACTIVATED in w.states), None)
    if current and current.workspaces:
        here = current.workspaces
    else:
        here = active_ws
    try:
        with open(STATE_FILE) as f:
            last = f.read().strip()
    except OSError:
        last = ""
    # Minimized windows are skipped, except the one we hid ourselves.
    candidates = [w for w in windows
                  if w.workspaces & here and (STATE_MINIMIZED not in w.states or w.id == last)]

    if "--list" in sys.argv:
        for w in candidates:
            mark = "*" if w is current else " "
            print(f"{mark} {w.app_id:20} {str(w.geometry):24} {sorted(w.states)} {w.title[:40]}")
        display.disconnect()
        return

    others = [w for w in candidates if w is not current]
    if not others:
        display.disconnect()
        return

    target = next((w for w in others if w.id == last), None)
    if target is None:
        # Fall back to the window after the current one, in stacking order.
        idx = candidates.index(current) if current in candidates else -1
        target = candidates[(idx + 1) % len(candidates)]
        if target is current:
            target = others[0]

    if current and current.id:
        try:
            with open(STATE_FILE, "w") as f:
                f.write(current.id)
        except OSError:
            pass

    manager = g[ZcosmicToplevelManagerV1.name]
    restoring = STATE_MINIMIZED in target.states
    if restoring:
        manager.unset_minimized(target.cosmic)
    manager.activate(target.cosmic, g[WlSeat.name])
    # Only hide the current window when it is the floating one on top. The
    # protocol doesn't say which window floats, so take the smaller of the
    # two overlapping ones; when restoring a hidden window, the current one
    # is the background and stays.
    if (current and not restoring and current.overlaps(target)
            and current.area() < target.area()):
        manager.set_minimized(current.cosmic)
    display.roundtrip()
    display.disconnect()


if __name__ == "__main__":
    main()
