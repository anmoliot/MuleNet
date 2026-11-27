"""Single bounded GNN process; a deadline kills computation, not just its waiter."""

import multiprocessing as mp
import queue
import threading
import time
from pathlib import Path


def _worker(model_path, incoming, outgoing, ready):
    import torch

    torch.set_num_threads(1)
    model = torch.jit.load(model_path, map_location="cpu").eval()
    ready.set()
    while True:
        values = incoming.get()
        if values is None:
            return
        try:
            x, edges, attributes = [torch.from_numpy(value) for value in values]
            with torch.no_grad():
                outgoing.put((True, torch.sigmoid(model(x, edges, attributes)).numpy()))
        except Exception:
            outgoing.put((False, "GNN inference failed"))


class GnnDeadline:
    def __init__(self, model_path: Path, timeout_seconds=0.2, cooldown_seconds=30):
        self.context = mp.get_context("spawn")
        self.path = str(model_path)
        self.timeout = timeout_seconds
        self.cooldown = cooldown_seconds
        self.lock = threading.Lock()
        self.failures = 0
        self.open_until = 0.0
        self.process = None
        self._start()

    def _start(self):
        self.incoming = self.context.Queue(maxsize=1)
        self.outgoing = self.context.Queue(maxsize=1)
        self.ready = self.context.Event()
        self.process = self.context.Process(
            target=_worker, args=(self.path, self.incoming, self.outgoing, self.ready), daemon=True
        )
        self.process.start()

    def predict(self, graph):
        if time.monotonic() < self.open_until:
            raise TimeoutError("GNN circuit open")
        if not self.lock.acquire(blocking=False):
            raise TimeoutError("GNN capacity occupied")
        try:
            if self.process is None or not self.process.is_alive():
                self._start()
            if not self.ready.is_set():
                raise TimeoutError("GNN warming")
            self.incoming.put_nowait((graph.x.numpy(), graph.edge_index.numpy(), graph.edge_attr.numpy()))
            try:
                ok, values = self.outgoing.get(timeout=self.timeout)
            except queue.Empty:
                self.close()
                self.failures += 1
                self.open_until = time.monotonic() + self.cooldown
                raise TimeoutError("GNN hard deadline exceeded; process terminated") from None
            if not ok:
                self.failures += 1
                if self.failures >= 3:
                    self.open_until = time.monotonic() + self.cooldown
                raise RuntimeError(values)
            self.failures = 0
            return values
        finally:
            self.lock.release()

    def close(self):
        if self.process:
            self.process.terminate()
            self.process.join(timeout=0.2)
            if self.process.is_alive():
                self.process.kill()
                self.process.join(timeout=0.2)
            self.process = None
            # A killed reader can leave the multiprocessing feeder blocked on a pipe.
            for channel in (self.incoming, self.outgoing):
                channel.cancel_join_thread()
                channel.close()
