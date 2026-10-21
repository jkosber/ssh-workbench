"""Child-only harness: exercise real fixture guards above harmless outer sentinels.

Both dispatch paths are substituted, including on their native OS. Changing only
the fixture/links module's sys reference leaves asyncio and Textual on the actual
host platform. A Linux case on Windows therefore proves simulated GIO-path
behavior, not native Linux operation.
"""

import asyncio
import importlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from threading import Event, current_thread
from types import SimpleNamespace
from unittest.mock import patch


def boundary_values(boundaries: tuple[str, ...]) -> dict[str, object]:
    values = {}
    for name in boundaries:
        owner, attribute = name.rsplit(".", 1)
        # shutil is a module attribute of links, not an importable submodule.
        if owner == "ssh_workbench.links.shutil":
            module = importlib.import_module("ssh_workbench.links").shutil
        else:
            module = importlib.import_module(owner)
        values[name] = getattr(module, attribute)
    return values


def main() -> None:
    root = Path(sys.argv[1]).resolve()
    scenario, *options = sys.argv[2:]
    # -I deliberately excludes inherited source paths; select this candidate.
    # The fixture under test imports the shared guard list from scripts/.
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root / "scripts"))
    shared = importlib.import_module("external_boundaries")
    boundaries = (
        *shared.EXTERNAL_BOUNDARIES,
        shared.WINDOWS_OPENER,
        "ssh_workbench.links.shutil.which",
        "ssh_workbench.app.open_link",
        "ssh_workbench.app.launch_ssh",
    )
    app_module = importlib.import_module("ssh_workbench.app")
    links = importlib.import_module("ssh_workbench.links")
    outer_calls = []
    dispatch_reached = Event()

    def reject_external_action(*args, **kwargs):
        outer_calls.append("unexpected external boundary")
        raise AssertionError("Unexpected external action in fixture test child")

    def outer_windows(url):
        outer_calls.append(url)
        dispatch_reached.set()

    def outer_gio(argv, **kwargs):
        assert argv[:3] == ["/fictional/gio", "open", "--"]
        outer_calls.append(argv[3])
        dispatch_reached.set()
        return subprocess.CompletedProcess(argv, 0)

    # These independent sentinels remain for the child lifetime, even when the
    # pre-fix fixture restores its inner patches. No real opener is reachable.
    for boundary in shared.EXTERNAL_BOUNDARIES:
        patch(boundary, side_effect=reject_external_action).start()
    patch(shared.WINDOWS_OPENER, outer_windows, create=True).start()
    patch("subprocess.run", outer_gio).start()
    patch("ssh_workbench.links.shutil.which", return_value="/fictional/gio").start()
    patch.dict(os.environ, {"DISPLAY": ":outer-fixture"}).start()

    before_import = boundary_values(boundaries)
    before_environment = dict(os.environ)
    fixture_path = root / "scripts" / "check_links.py"
    spec = importlib.util.spec_from_file_location(
        "link_fixture_under_test", fixture_path
    )
    assert spec is not None and spec.loader is not None
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    assert boundary_values(boundaries) == before_import, (
        "Import changed an external boundary"
    )
    assert dict(os.environ) == before_environment, "Import changed the environment"
    if scenario == "import":
        assert not outer_calls
        print("Import left boundaries unchanged", flush=True)
        return

    platform, ending = options
    # Never replace global sys.platform: that could alter the host event loop.
    platform_view = SimpleNamespace(platform=platform)
    fixture.sys = platform_view
    links.sys = platform_view
    sys.argv = [str(fixture_path)]
    entered, release, finished = Event(), Event(), Event()
    fixture_calls, worker_threads, apps, installed_guards = [], [], [], []
    original_validate = links.validate_http_url
    original_dispatch = fixture.simulate_dispatch
    original_open_link = fixture.open_link

    def delayed_validation(url):
        # Arrival inside real open_link proves the worker passed _links_closed.
        entered.set()
        assert release.wait(10), "Fixture entry point did not release validation"
        return original_validate(url)

    def observed_fixture_dispatch(url):
        fixture_calls.append(url)
        worker_threads.append(current_thread())
        dispatch_reached.set()
        if scenario == "blocked":
            entered.set()
        return original_dispatch(url)

    def observed_open_link(url):
        try:
            return original_open_link(url)
        finally:
            finished.set()

    fixture.simulate_dispatch = observed_fixture_dispatch
    fixture.open_link = observed_open_link
    if scenario == "race":
        links.validate_http_url = delayed_validation

    async def drive_quit(app):
        # The Windows loop's local socket pair exists before these extra guards.
        with (
            patch("socket.socket.connect", side_effect=reject_external_action),
            patch("socket.socket.connect_ex", side_effect=reject_external_action),
        ):
            async with app.run_test(size=(80, 24)) as pilot:
                if scenario == "blocked":
                    await pilot.press(*(["down"] * (len(fixture.MACHINES) - 1)))
                await pilot.press("o")
                async with asyncio.timeout(5):
                    while not entered.is_set():
                        await pilot.pause()
                assert app._link_request is not None
                assert not finished.is_set()
                await pilot.press(ending if scenario == "blocked" else "q")
                assert not app.is_running and app.return_code == 0
            assert app._links_closed.is_set()
            assert app._link_request is None

    def run_headless(app):
        apps.append(app)
        installed_guards.append(boundary_values(boundaries))
        asyncio.run(drive_quit(app))
        if scenario == "race" and ending == "error":
            raise RuntimeError("Controlled fixture run error")
        if scenario == "race" and ending == "interrupt":
            raise KeyboardInterrupt("Controlled fixture run interrupt")

    patch.object(app_module.SSHWorkbenchApp, "run", run_headless).start()
    try:
        result = fixture.main()
    except (RuntimeError, KeyboardInterrupt) as error:
        assert scenario == "race" and ending in {"error", "interrupt"}
        expected = RuntimeError if ending == "error" else KeyboardInterrupt
        assert type(error) is expected
    else:
        assert scenario == "blocked" or ending == "return"
        assert result == 0
    assert len(apps) == 1 and apps[0]._links_closed.is_set()
    assert entered.is_set() and not finished.is_set()
    if scenario == "blocked":
        assert fixture_calls == [fixture.MACHINES[-1].links[0].url]
        assert not outer_calls
        assert worker_threads[0].daemon and worker_threads[0].is_alive()
        assert boundary_values(boundaries) == installed_guards[0], (
            "Fixture restored its guards"
        )
        print(
            f"Blocked {platform}/{ending}: fixture returned with daemon still blocked",
            flush=True,
        )
        # Normal return must let the interpreter exit while the fixture's actual
        # blocked stub still waits forever; no forced exit or thread release.
        return

    # This release happens only after the actual fixture.main has returned or
    # unwound. The pre-fix context manager has already removed its guards here.
    release.set()
    assert dispatch_reached.wait(5), "Worker never reached either dispatch sentinel"
    assert finished.wait(5), "Released worker did not complete open_link"
    guards_retained = boundary_values(boundaries) == installed_guards[0]
    print(
        f"Race {platform}/{ending}: fixture dispatch={len(fixture_calls)}, "
        f"outer dispatch={len(outer_calls)}; guards retained={guards_retained}",
        flush=True,
    )
    assert not outer_calls, f"Delayed worker escaped fixture guards: {outer_calls!r}"
    assert fixture_calls == [fixture.MACHINES[0].links[0].url]
    assert guards_retained, "Fixture restored its guards"


if __name__ == "__main__":
    main()
