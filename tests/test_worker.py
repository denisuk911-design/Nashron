from gui.worker import GenerateWorker


class FailingPromptBuilder:
    def build(self, *_args, **_kwargs):
        raise AssertionError("A cancelled worker must not build a prompt")


class FakeClient:
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def generate(self, *_args, **_kwargs):
        raise AssertionError("A cancelled worker must not start a provider")


def test_cancelled_worker_finishes_without_starting_provider():
    client = FakeClient()
    worker = GenerateWorker(FailingPromptBuilder(), client, 1, "message")
    results = []
    worker.finished_with_result.connect(results.append)

    worker.cancel()
    worker.run()

    assert client.cancelled
    assert len(results) == 1
    assert results[0].cancelled
