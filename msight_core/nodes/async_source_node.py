import asyncio
from abc import ABC, abstractmethod

from .base import NodeConfig, SourceNode


class AsyncSourceNode(SourceNode, ABC):
    """
    Base class for async source nodes that:
    - repeatedly await some async receive operation,
    - optionally process the message,
    - publish it into MSight,
    - handle gap + heartbeat + on_before/after_iteration.

    Subclasses must implement:
      - async _recv_once(self) -> Any
        (get the next raw message, or raise StopAsyncIteration to stop)

    Optionally override:
      - async _async_setup(self)
      - on_message(self, data)
    """

    def __init__(self, configs: NodeConfig):
        super().__init__(configs=configs)

    def _spin(self, life_span: int = -1):
        """
        Synchronous entrypoint used by the node runner.

        For async nodes we just run the async loop forever.
        """
        assert life_span == -1, "AsyncSourceNode does not support life_span"
        try:
            asyncio.run(self._spin_async())
        except KeyboardInterrupt:
            self.logger.info(f"{self.name} interrupted, shutting down...")

    async def _spin_async(self):
        """
        Main async loop:
        - optional async setup
        - receive gap filter on_message publish
        - heartbeat
        """
        await self._async_setup()

        while True:
            try:
                data = await self._recv_once()
            except StopAsyncIteration:
                self.logger.info(f"{self.name} stopped by StopAsyncIteration.")
                break
            except Exception as e:
                self.logger.error(
                    f"{self.name} error in _recv_once: {e}",
                    exc_info=True
                )
                break

            self.on_before_iteration()

            if self.gap_counter.countdown():
                processed = self.on_message(data)
                if processed is not None:
                    self.publish(processed)

            self.on_after_iteration()

            # heartbeat (if configured)
            if self.heartbeat_counter.countdown():
                # print("heartbeat")
                self.heartbeat()

    # ---- Hooks for subclasses ----

    async def _async_setup(self):
        """
        Optional async setup hook (e.g., open a connection).
        Default: no-op.
        """
        return

    @abstractmethod
    async def _recv_once(self):
        """
        Must return the next raw message.

        Raise StopAsyncIteration to stop the node gracefully.
        """
        ...

    def on_message(self, data):
        """
        Optional data processing hook.

        Default: pass-through.
        Subclasses often want to wrap into a Data type (e.g., BytesData).
        """
        return data

