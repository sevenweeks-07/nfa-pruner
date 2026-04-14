"""
nfa_engine.py
Builds a multi-pattern NFA and runs two simulation modes:
  standard  - tracks all active states, evaluates transitions from each one
  pruned    - skips states whose required chars are absent from the input window
"""

from collections import defaultdict, deque


# each NFA state is just a dict: char -> list of target state ids
# plus a set of chars it can transition on (used for pruning)

class MultiPatternNFA:
    """
    Simple multi-pattern NFA.
    State 0 is the shared start state.
    Each pattern adds a chain of states off state 0.
    """

    def __init__(self, patterns):
        self.transitions   = defaultdict(lambda: defaultdict(set))
        self.accept_states = set()
        self.state_chars   = defaultdict(set)  # state -> set of chars it listens to
        self._build(patterns)

    def _build(self, patterns):
        sid = 1  # state 0 is start
        for pat in patterns:
            prev = 0
            for ch in pat:
                self.transitions[prev][ch].add(sid)
                self.state_chars[prev].add(ch)   # prev listens to ch
                prev = sid
                sid += 1
            self.accept_states.add(prev - 1)     # last state of chain

    def run_standard(self, data):
        """
        Standard NFA simulation.
        For each byte, compute transitions from every active state.
        Cost = O(|active_states|) per byte.
        """
        active  = {0}
        matches = 0
        evals   = 0

        for byte in data:
            ch       = chr(byte)
            next_set = {0}            # start always re-added (overlapping search)
            for sid in active:
                evals += 1            # one evaluation per active state per byte
                next_set.update(self.transitions[sid].get(ch, set()))
            active = next_set
            if active & self.accept_states:
                matches += 1

        return {'matches': matches, 'evals': evals, 'skipped': 0}

    def run_pruned(self, data, window):
        """
        Pruned NFA simulation.
        Before evaluating transitions from a state, check if any of its
        required chars appear in the current window (Sigma').
        If none do, that state cannot fire -> skip it.
        This saves real work when active set contains states for rare chars.
        """
        active  = {0}
        matches = 0
        evals   = 0
        skipped = 0

        for byte in data:
            ch      = chr(byte)
            allowed = window.update(byte)      # Sigma' after this byte
            next_set = {0}

            for sid in active:
                needed = self.state_chars.get(sid)
                # if this state needs chars and none are in window, skip it
                if needed and not (needed & allowed):
                    skipped += 1
                    continue
                evals += 1
                next_set.update(self.transitions[sid].get(ch, set()))

            active = next_set
            if active & self.accept_states:
                matches += 1

        return {'matches': matches, 'evals': evals, 'skipped': skipped}
