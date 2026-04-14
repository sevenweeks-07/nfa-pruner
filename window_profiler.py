"""
window_profiler.py
Tracks which characters have appeared in the last W bytes.
This is Sigma' -- the active character set used for pruning.
Update is O(1) per byte using a deque + frequency dict.
"""

from collections import deque


class WindowProfiler:

    def __init__(self, window_size=32):
        self.W       = window_size
        self._buf    = deque()     # last W bytes
        self._freq   = {}          # char -> count
        self._active = set()       # current Sigma'

    def update(self, byte):
        """Slide window forward one byte. Returns current Sigma'."""
        ch = chr(byte)

        # evict oldest if full
        if len(self._buf) == self.W:
            old = self._buf.popleft()
            self._freq[old] -= 1
            if self._freq[old] == 0:
                del self._freq[old]
                self._active.discard(old)

        self._buf.append(ch)
        self._freq[ch] = self._freq.get(ch, 0) + 1
        self._active.add(ch)
        return self._active

    @property
    def allowed(self):
        return self._active

    def reset(self):
        self._buf.clear()
        self._freq.clear()
        self._active.clear()
