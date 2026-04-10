class CapabilityRegistry:
    def __init__(self):
        self._handlers = {}

    def register(self, capability: str, handler):
        self._handlers[capability] = handler

    def get(self, capability: str):
        return self._handlers.get(capability)
