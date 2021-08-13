"""This module provides utility functions that don't fit elsewhere."""
# TODO: move PoW Generator here

import queue


# FIFO Queue which will not add duplicates
# Source: https://stackoverflow.com/a/16506527
class SetQueue(queue.Queue):
    # Use a set as a basis to avoid duplicates
    def _init(self, maxsize):
        self.queue = set()

    def _put(self, item):
        self.queue.add(item)

    def _get(self):
        return self.queue.pop()

    def contains(self, item):
        with self.mutex:
            return item in self.queue
