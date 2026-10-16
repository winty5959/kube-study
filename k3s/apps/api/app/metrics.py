from prometheus_client import Counter, Histogram
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector

UPLOADS = Counter("album_uploads_total", "Photo upload attempts", ["status"])

REQUEST_DURATION = Histogram(
    "album_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route", "status"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)


class QueueLengthCollector(Collector):
    """Reads the Redis queue length at scrape time so the value is never stale."""

    def __init__(self, redis_client, queue_key: str):
        self._redis = redis_client
        self._key = queue_key

    def collect(self):
        gauge = GaugeMetricFamily("album_queue_length", "Pending thumbnail jobs in Redis")
        try:
            gauge.add_metric([], self._redis.llen(self._key))
        except Exception:
            return  # omit the sample when Redis is unreachable rather than report a fake 0
        yield gauge
