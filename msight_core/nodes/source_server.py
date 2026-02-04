from abc import ABC, abstractmethod
from .base import SourceNode, NodeConfig
from .utils import Counter


class ServerSourceNode(SourceNode, ABC):
    """
    Base class for server-style source nodes.

    Subclass responsibilities:
    - Implement `initialize()` to set up the server and hook its
      message handler so that it calls `self.handle_incoming(data)`.
    - Implement `serve()` to run the server loop. This is called
      by `_spin()` / `spin()`.

    You MAY override `__init__`, but you MUST:
    - call super().__init__(configs)
    - ensure that initialize() is called (either by relying on the base
      __init__ calling it, or by calling self.initialize() yourself).
    """

    def __init__(self, configs: NodeConfig):
        SourceNode.__init__(self, configs=configs)
        # Track whether the subclass bound its server callbacks to handle_incoming
        # print(self.sensor_name)
        

    @classmethod
    def create(cls, name, publish_topic_name, gap=0):
        raise NotImplementedError("Subclasses must implement the create() factory method.")

    @abstractmethod
    def initialize(self):
        """
        Initialize the server source node.

        This is where subclasses should:
        - create/configure the underlying server object
        - hook the server's message handling so that it calls
          `self.handle_incoming(data)` for each received message

        If you override __init__, you are responsible for ensuring
        initialize() is called at least once.
        """
        raise NotImplementedError

    @abstractmethod
    def serve(self):
        """
        Start serving incoming connections.

        This method should block and run the main server loop, calling
        `self.handle_incoming(data)` whenever a new message arrives.
        """
        raise NotImplementedError


    def handle_incoming(self, raw_data):
        """
        Wrapper to be called by the server whenever a message is received.

        Subclasses normally do NOT override this. They should:
        - convert raw input into a Data instance *before* calling this
          (e.g., ImageData(frame, timestamp, sensor_name))
        - then call: self.handle_incoming(data_obj)
        """
        self.on_before_iteration()

        if self.gap_counter.countdown():
            # As a source node, we assume data is already a Data object
            processed_data = self.on_message(raw_data)
            if processed_data is not None:
              self.publish(processed_data)

        self.on_after_iteration()

        if self.heartbeat_counter.countdown():
            self.heartbeat()

        # if self.life_counter.countdown():
        #     self.unregister()
        #     self._kill_process()

    def _spin(self, life_span: int = -1):
        # Server lifetime is controlled entirely by serve()
        # self.life_counter = Counter(life_span)
        assert life_span == -1, "ServerSourceNode does not support life_span"
        self.initialize()
        self.serve()

    def start(self):
        """User-friendly alias for spin()."""
        self.spin()

    @abstractmethod
    def on_message(self, data):
        '''
        You have to override this method if you want to process the data before publishing.
        '''
        raise NotImplementedError("Subclasses must implement on_message() to process incoming data.")

