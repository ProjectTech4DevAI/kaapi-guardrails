import time
import tracemalloc

class Profiler:
    def __enter__(self):
        self.latencies = []
        tracemalloc.start()
        return self

    def record(self, fn, *args):
        start = time.perf_counter()
        result = fn(*args)
        self.latencies.append((time.perf_counter() - start) * 1000)
        return result

    def __exit__(self, *args):
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.peak_memory_mb = peak / (1024 * 1024)
