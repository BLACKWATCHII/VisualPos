"""Motor de PDF con un Chromium persistente.

Antes, cada descarga hacía `node generate_pdf.js` => arrancar Node + abrir un
Chromium nuevo (~2 s) por PDF. Ahora se mantiene un único proceso
`pdfgen/pdf_worker.js` vivo y se le mandan trabajos por stdin.

`run_pdf_job(html_path, pdf_path)` devuelve un `subprocess.CompletedProcess`
igual que el `subprocess.run([...])` que reemplaza, así el código que lo llama
no cambia. Si el worker falla o no responde, se usa el script de un solo uso
(`generate_pdf.js`) como respaldo, de modo que nunca queda peor que antes.
"""
import json
import logging
import os
import queue
import subprocess
import threading
import uuid

from django.conf import settings

logger = logging.getLogger(__name__)

PDF_DIR = os.path.join(settings.BASE_DIR, 'pdfgen')
WORKER_SCRIPT = os.path.join(PDF_DIR, 'pdf_worker.js')
ONE_SHOT_SCRIPT = os.path.join(PDF_DIR, 'generate_pdf.js')
JOB_TIMEOUT = int(os.getenv('PDF_JOB_TIMEOUT', '60'))
WORKER_ENABLED = os.getenv('PDF_WORKER_ENABLED', '1') != '0'


class _PdfWorker:
    def __init__(self):
        self._proc = None
        self._lock = threading.Lock()           # protege arranque/escritura
        self._waiters = {}                      # id -> queue.Queue
        self._waiters_lock = threading.Lock()

    # -- ciclo de vida -----------------------------------------------------
    def _alive(self):
        return self._proc is not None and self._proc.poll() is None

    def _start(self):
        self._proc = subprocess.Popen(
            ['node', WORKER_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding='utf-8',
            bufsize=1,
            cwd=PDF_DIR,
        )
        proc = self._proc
        threading.Thread(target=self._read_loop, args=(proc,), daemon=True, name='pdf-worker-reader').start()

    def _read_loop(self, proc):
        for line in proc.stdout:
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            with self._waiters_lock:
                waiter = self._waiters.get(msg.get('id'))
            if waiter is not None:
                waiter.put(msg)
        # El proceso murió: despertar a quien estuviera esperando
        with self._waiters_lock:
            for waiter in self._waiters.values():
                try:
                    waiter.put_nowait({'ok': False, 'error': 'El worker de PDF terminó inesperadamente.'})
                except queue.Full:
                    pass

    def _kill(self):
        if self._proc is not None:
            try:
                self._proc.kill()
            except OSError:
                pass
        self._proc = None

    # -- API ---------------------------------------------------------------
    def render(self, html_path, pdf_path, timeout):
        job_id = uuid.uuid4().hex
        waiter = queue.Queue(maxsize=1)
        with self._waiters_lock:
            self._waiters[job_id] = waiter
        try:
            with self._lock:
                if not self._alive():
                    self._start()
                self._proc.stdin.write(json.dumps({'id': job_id, 'html': html_path, 'out': pdf_path}) + '\n')
                self._proc.stdin.flush()
            try:
                msg = waiter.get(timeout=timeout)
            except queue.Empty:
                with self._lock:
                    self._kill()   # colgado: se reinicia en el próximo trabajo
                return False, f'El worker de PDF no respondió en {timeout} s.'
            return bool(msg.get('ok')), msg.get('error') or ''
        finally:
            with self._waiters_lock:
                self._waiters.pop(job_id, None)


_worker = _PdfWorker()


def warm_up_in_background():
    """Arranca Node + Chromium al iniciar el servidor para que el primer PDF
    no pague ~3 s de arranque en frío."""
    if not WORKER_ENABLED:
        return

    def _start():
        try:
            with _worker._lock:
                if not _worker._alive():
                    _worker._start()
        except Exception as exc:  # noqa: BLE001
            logger.warning('No se pudo precalentar el worker de PDF: %s', exc)

    threading.Thread(target=_start, daemon=True, name='pdf-worker-warmup').start()


def should_warm_up(argv, environ):
    """Solo en el proceso que atiende peticiones (no en migrate, shell, etc.)."""
    if environ.get('PDF_WORKER_PREWARM') == '1':
        return True
    if 'runserver' not in argv:
        return False
    # Con autoreload, el proceso hijo es el que atiende (RUN_MAIN=true)
    return environ.get('RUN_MAIN') == 'true' or '--noreload' in argv


def _run_one_shot(html_path, pdf_path, timeout):
    return subprocess.run(
        ['node', ONE_SHOT_SCRIPT, html_path, pdf_path],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_pdf_job(html_path, pdf_path, timeout=JOB_TIMEOUT):
    """Convierte html_path -> pdf_path. Devuelve CompletedProcess (returncode 0 = ok)."""
    args = ['pdf_worker', html_path, pdf_path]
    if WORKER_ENABLED:
        try:
            ok, error = _worker.render(os.path.abspath(html_path), os.path.abspath(pdf_path), timeout)
            if ok and os.path.exists(pdf_path):
                return subprocess.CompletedProcess(args, 0, stdout='', stderr='')
            logger.warning('Worker de PDF falló, usando respaldo de un solo uso: %s', error)
        except Exception as exc:  # noqa: BLE001 - cualquier fallo del worker cae al respaldo
            logger.warning('Worker de PDF no disponible, usando respaldo: %s', exc)
    return _run_one_shot(html_path, pdf_path, timeout)
