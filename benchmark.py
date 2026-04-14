"""
benchmark.py
All benchmarks for Input-Aware NFA State Pruning (PS5).
Run this file to reproduce all results in the report.
"""

import random
import time
from nfa_engine import MultiPatternNFA
from window_profiler import WindowProfiler

random.seed(42)


def gen_http(n=200):
    methods = ['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS']
    paths   = ['/api/users', '/api/data', '/home', '/index.html',
               '/static/main.css', '/health', '/api/v2/products']
    hdrs    = ['Host: example.com', 'Accept: application/json',
               'Content-Type: text/html', 'Connection: keep-alive',
               'Authorization: Bearer abc123', 'User-Agent: Mozilla/5.0']
    lines = []
    for _ in range(n):
        lines.append(f'{random.choice(methods)} {random.choice(paths)} HTTP/1.1')
        for h in random.sample(hdrs, 3):
            lines.append(h)
        lines.append('')
    return '\n'.join(lines).encode('ascii')


def gen_dns(n=300):
    words = ['example','google','api','cdn','mail','blog','shop','dev',
             'news','app','www','static','assets','media','files']
    tlds  = ['.com', '.net', '.org', '.io', '.co.uk']
    lines = []
    for _ in range(n):
        d = '.'.join(random.sample(words, random.randint(1, 3)))
        lines.append(f'QUERY {d}{random.choice(tlds)} A')
    return '\n'.join(lines).encode('ascii')


def gen_json(n=150):
    import json
    records = []
    for i in range(n):
        records.append(json.dumps({
            'id': i, 'name': f'user_{i}',
            'email': f'user{i}@example.com',
            'score': round(random.uniform(0, 100), 2),
            'active': random.choice([True, False])
        }))
    return '\n'.join(records).encode('utf-8')


def gen_binary(n=50000):
    return bytes(random.randint(0, 255) for _ in range(n))


def gen_mixed(n_bytes=40000):
    http = gen_http(80)
    dns  = gen_dns(100)
    jsn  = gen_json(50)
    blob = gen_binary(5000)
    data = http + dns + jsn + blob
    return data[:n_bytes] if len(data) >= n_bytes else data


# 24 patterns covering HTTP, DNS, and protocol keywords.
# Each starts with a distinct first character, so the start state
# fans out to many first-states -- exactly what Sigma' can prune.
PATTERNS = [
    'GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS', 'PATCH', 'CONNECT',
    'HTTP', 'HOST', 'QUERY', 'RETURN', 'SELECT', 'WHERE', 'FROM', 'TABLE',
    'ACCEPT', 'CONTENT', 'LOCATION', 'VERSION', 'TRANSFER', 'UPGRADE',
    'AUTHORIZATION', 'USER'
]


def bench_correctness():
    print('\n[1] Correctness verification')
    print('-' * 56)

    nfa = MultiPatternNFA(PATTERNS)
    datasets = {
        'HTTP traffic': gen_http(100),
        'DNS traffic':  gen_dns(200),
        'JSON data':    gen_json(80),
        'Mixed':        gen_mixed(30000),
        'Binary':       gen_binary(20000),
    }

    all_pass = True
    for name, data in datasets.items():
        for W in [8, 16, 32, 64]:
            win = WindowProfiler(window_size=W)
            std = nfa.run_standard(data)
            prn = nfa.run_pruned(data, window=win)
            ok  = (std['matches'] == prn['matches'])
            if not ok:
                all_pass = False
            total = prn['evals'] + prn['skipped']
            ratio = prn['skipped'] / total if total else 0
            print(f"  [{'PASS' if ok else 'FAIL'}]  {name:<16}  W={W:3d}  "
                  f"matches={std['matches']:5d}  pruning={ratio:.1%}")

    print(f"\n  Overall: {'ALL TESTS PASSED' if all_pass else 'FAILURES DETECTED'}")
    return all_pass


def bench_reduction(W=32):
    print(f'\n[2] Transition reduction by input type  (W={W})')
    print('-' * 70)

    nfa = MultiPatternNFA(PATTERNS)
    datasets = {
        'HTTP traffic': gen_http(150),
        'DNS traffic':  gen_dns(250),
        'JSON data':    gen_json(100),
        'Mixed':        gen_mixed(40000),
        'Binary':       gen_binary(40000),
    }

    print(f"  {'Input':<16} {'Std evals':>11} {'Prn evals':>11} "
          f"{'Skipped':>11} {'Reduction':>10} {'Matches':>9}")
    print('  ' + '-'*68)

    results = {}
    for name, data in datasets.items():
        win = WindowProfiler(window_size=W)
        std = nfa.run_standard(data)
        prn = nfa.run_pruned(data, window=win)
        total = prn['evals'] + prn['skipped']
        red   = prn['skipped'] / total if total else 0
        print(f"  {name:<16} {std['evals']:>11,} {prn['evals']:>11,} "
              f"{prn['skipped']:>11,} {red:>9.1%} {std['matches']:>9,}")
        results[name] = {
            'std_evals': std['evals'], 'prn_evals': prn['evals'],
            'skipped': prn['skipped'], 'reduction': red,
            'matches': std['matches']
        }
    return results

def bench_vs_w():
    print('\n[3] Pruning ratio vs window size W')
    print('-' * 60)

    nfa      = MultiPatternNFA(PATTERNS)
    ws       = [4, 8, 16, 32, 64, 128, 256]
    datasets = {
        'HTTP':   gen_http(150),
        'DNS':    gen_dns(250),
        'JSON':   gen_json(100),
        'Mixed':  gen_mixed(40000),
        'Binary': gen_binary(40000),
    }

    header = f"  {'Input':<8}" + ''.join(f'  W={w:<4}' for w in ws)
    print(header)
    print('  ' + '-'*58)

    results = {}
    for name, data in datasets.items():
        row = {}
        line = f'  {name:<8}'
        for W in ws:
            win = WindowProfiler(window_size=W)
            r   = nfa.run_pruned(data, window=win)
            tot = r['evals'] + r['skipped']
            rat = r['skipped'] / tot if tot else 0
            line += f'  {rat:.1%} '
            row[W] = rat
        print(line)
        results[name] = row
    return results

def bench_throughput():
    print('\n[4] Throughput comparison (MB/s)  averaged over 5 runs')
    print('-' * 60)

    nfa    = MultiPatternNFA(PATTERNS)
    N_RUNS = 5
    W      = 32

    datasets = {
        'HTTP (~80KB)':  gen_http(400),
        'DNS (~60KB)':   gen_dns(400),
        'Binary (50KB)': gen_binary(50000),
    }

    print(f"  {'Dataset':<18} {'Std MB/s':>10} {'Prn MB/s':>12} {'Ratio':>8}")
    print('  ' + '-'*52)

    results = {}
    for name, data in datasets.items():
        mb = len(data) / 1e6

        t0 = time.perf_counter()
        for _ in range(N_RUNS):
            nfa.run_standard(data)
        std_mbps = mb / ((time.perf_counter() - t0) / N_RUNS)

        t0 = time.perf_counter()
        for _ in range(N_RUNS):
            win = WindowProfiler(W)
            nfa.run_pruned(data, window=win)
        prn_mbps = mb / ((time.perf_counter() - t0) / N_RUNS)

        ratio = prn_mbps / std_mbps
        print(f"  {name:<18} {std_mbps:>10.2f} {prn_mbps:>12.2f} {ratio:>7.2f}x")
        results[name] = {'std': std_mbps, 'prn': prn_mbps, 'ratio': ratio}
    return results

def bench_vs_patterns():
    print('\n[5] Effect of pattern count on pruning  (HTTP input, W=32)')
    print('-' * 55)

    data = gen_http(150)
    sets = [
        PATTERNS[:4],
        PATTERNS[:8],
        PATTERNS[:12],
        PATTERNS[:16],
        PATTERNS[:20],
        PATTERNS,
    ]

    print(f"  {'Patterns':>10} {'States':>8} {'Std evals':>11} "
          f"{'Skipped':>11} {'Reduction':>10}")
    print('  ' + '-'*54)

    results = {}
    for pset in sets:
        nfa   = MultiPatternNFA(pset)
        win   = WindowProfiler(32)
        std   = nfa.run_standard(data)
        prn   = nfa.run_pruned(data, window=win)
        total = prn['evals'] + prn['skipped']
        red   = prn['skipped'] / total if total else 0
        n_states = sum(len(t) for t in nfa.transitions.values()) + 1
        print(f"  {len(pset):>10} {n_states:>8} {std['evals']:>11,} "
              f"{prn['skipped']:>11,} {red:>9.1%}")
        results[len(pset)] = red
    return results


if __name__ == '__main__':
    print('=' * 60)
    print('NSD PS5 — Input-Aware NFA State Activation Pruning')
    print('Benchmark Suite')
    print('=' * 60)

    bench_correctness()
    bench_reduction()
    bench_vs_w()
    bench_throughput()
    bench_vs_patterns()

    print('\n[Done] Run plot_results.py to generate figures.')
