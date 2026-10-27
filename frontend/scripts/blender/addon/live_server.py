# Live session server: run inside Blender's GUI (`run.py blender` starts Blender with
# it). Listens on 127.0.0.1 only; each connection sends Python source, which runs on
# Blender's main thread, and gets back {"ok", "output", "error"} as JSON. That lets
# builds happen in the open session, so changes appear in the viewport as they land.
import contextlib, io, json, os, queue, socket, sys, threading, traceback
import bpy

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
with open(os.path.join(HERE, "blender.json")) as f:
    PORT = json.load(f).get("port", 9876)

_requests = queue.Queue()
_namespace = {"bpy": bpy, "__name__": "__live__"}

def _serve(sock):
    while True:
        conn, _ = sock.accept()
        chunks = []
        while True:
            data = conn.recv(65536)
            if not data:
                break
            chunks.append(data)
        _requests.put((b"".join(chunks).decode(), conn))

def _pump():
    # Timer callback on the main thread: bpy is only safe to touch here.
    while not _requests.empty():
        code, conn = _requests.get_nowait()
        out = io.StringIO()
        reply = {"ok": True, "output": "", "error": None}
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                exec(compile(code, "<live>", "exec"), _namespace)
        except Exception:
            reply.update(ok=False, error=traceback.format_exc())
        reply["output"] = out.getvalue()
        try:
            conn.sendall(json.dumps(reply).encode())
        finally:
            conn.close()
    return 0.1

def start():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("127.0.0.1", PORT))
    except OSError:
        print(f"live server: port {PORT} is busy (another session running?)")
        return
    sock.listen(4)
    threading.Thread(target=_serve, args=(sock,), daemon=True).start()
    bpy.app.timers.register(_pump, persistent=True)
    print(f"live server: listening on 127.0.0.1:{PORT}")

start()
