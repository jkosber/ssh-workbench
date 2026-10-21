"""Process, network and browser entry points that checks and fixtures guard."""

# Tests, fixtures and the package check reject these dotted names.
EXTERNAL_BOUNDARIES = (
    "socket.create_connection",
    "socket.getaddrinfo",
    "subprocess.Popen",
    "subprocess.run",
    "os.system",
    "webbrowser.open",
    "webbrowser.open_new",
    "webbrowser.open_new_tab",
    "asyncio.create_subprocess_exec",
    "asyncio.create_subprocess_shell",
)
# Exists only on Windows. The link fixture substitutes it instead of rejecting it.
WINDOWS_OPENER = "os.startfile"
