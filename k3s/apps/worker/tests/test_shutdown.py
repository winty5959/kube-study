from collections import deque
from types import SimpleNamespace

from worker.main import Worker


def test_signal_during_blocking_pop_returns_the_unclaimed_job():
    worker = object.__new__(Worker)
    worker.s = SimpleNamespace(queue_key="jobs", processing_key="processing", poll_timeout_s=5)
    worker.stopping = False
    worker.heartbeat = SimpleNamespace(beat=lambda: None)
    closed = []
    worker.pool = SimpleNamespace(open=lambda **kwargs: None, close=lambda: closed.append(True))
    worker.recover_inflight = lambda: None
    processed = []
    worker.process = processed.append
    queues = {"jobs": deque([b"photo"]), "processing": deque()}

    def pop(source, destination, timeout, source_side, destination_side):
        assert (timeout, source_side, destination_side) == (5, "RIGHT", "LEFT")
        item = queues[source].pop()
        queues[destination].appendleft(item)
        worker.stopping = True  # The signal arrived while waiting for this item.
        return item

    def move(source, destination, source_side, destination_side):
        assert (source_side, destination_side) == ("LEFT", "RIGHT")
        item = queues[source].popleft()
        queues[destination].append(item)
        return item

    worker.redis = SimpleNamespace(blmove=pop, lmove=move)
    worker.run()

    assert processed == []
    assert list(queues["jobs"]) == [b"photo"]
    assert list(queues["processing"]) == []
    assert closed == [True]
