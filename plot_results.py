"""
plot_results.py
Generates all 5 figures for the report.
Run after benchmark.py to produce figures/ directory.
"""

import random
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from nfa_engine import MultiPatternNFA
from window_profiler import WindowProfiler
from benchmark import (gen_http, gen_dns, gen_json, gen_binary, gen_mixed, PATTERNS)

random.seed(42)
os.makedirs('figures', exist_ok=True)

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11})



def fig1():
    nfa = MultiPatternNFA(PATTERNS)
    ws  = [4, 8, 16, 32, 64, 128, 256]

    datasets = {
        'HTTP traffic':  (gen_http(150),    '#2196F3', 'o'),
        'DNS traffic':   (gen_dns(250),     '#4CAF50', 's'),
        'JSON data':     (gen_json(100),    '#FF9800', '^'),
        'Mixed traffic': (gen_mixed(40000), '#9C27B0', 'D'),
        'Binary data':   (gen_binary(40000),'#F44336', 'x'),
    }

    fig, ax = plt.subplots(figsize=(9, 5))

    for label, (data, color, marker) in datasets.items():
        ratios = []
        for W in ws:
            win = WindowProfiler(W)
            r   = nfa.run_pruned(data, window=win)
            tot = r['evals'] + r['skipped']
            ratios.append(r['skipped'] / tot * 100 if tot else 0)
        ax.plot(ws, ratios, marker=marker, color=color,
                linewidth=2, markersize=7, label=label)

    ax.set_xscale('log', base=2)
    ax.set_xticks(ws)
    ax.set_xticklabels([str(w) for w in ws])
    ax.set_xlabel('Window size W (bytes)')
    ax.set_ylabel('Average pruning ratio (%)')
    ax.set_title('Fig 1 — NFA State Pruning Ratio vs Window Size W')
    ax.set_ylim(0, 105)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3, linestyle='--')

    plt.tight_layout()
    plt.savefig('figures/fig1_pruning_vs_window.png', dpi=150, bbox_inches='tight')
    plt.close()
    print('saved figures/fig1_pruning_vs_window.png')



def fig2():
    nfa = MultiPatternNFA(PATTERNS)
    W   = 32

    datasets = {
        'HTTP':   gen_http(150),
        'DNS':    gen_dns(250),
        'JSON':   gen_json(100),
        'Mixed':  gen_mixed(40000),
        'Binary': gen_binary(40000),
    }

    labels   = list(datasets.keys())
    evals    = []
    skipped  = []
    for data in datasets.values():
        win = WindowProfiler(W)
        r   = nfa.run_pruned(data, window=win)
        evals.append(r['evals'] / 1000)
        skipped.append(r['skipped'] / 1000)

    x  = np.arange(len(labels))
    bw = 0.38

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(x - bw/2, evals,   bw, label='Transitions evaluated', color='#2196F3', alpha=0.85)
    ax.bar(x + bw/2, skipped, bw, label='Transitions skipped (pruned)', color='#4CAF50', alpha=0.85)

    for i, (ev, sk) in enumerate(zip(evals, skipped)):
        tot = ev + sk
        pct = sk / tot * 100 if tot else 0
        ax.text(i + bw/2, sk + max(skipped)*0.01,
                f'{pct:.0f}%', ha='center', va='bottom',
                fontsize=9, color='#1B5E20', fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel('Input type')
    ax.set_ylabel('Transitions (thousands)')
    ax.set_title(f'Fig 2 — NFA Transitions Evaluated vs Skipped  (W={W})')
    ax.legend()
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')

    plt.tight_layout()
    plt.savefig('figures/fig2_transition_reduction.png', dpi=150, bbox_inches='tight')
    plt.close()
    print('  saved figures/fig2_transition_reduction.png')



def fig3():
    data = gen_http(150)
    W    = 32

    counts   = [4, 8, 12, 16, 20, 24]
    reductions = []

    for n in counts:
        nfa = MultiPatternNFA(PATTERNS[:n])
        win = WindowProfiler(W)
        r   = nfa.run_pruned(data, window=win)
        tot = r['evals'] + r['skipped']
        reductions.append(r['skipped'] / tot * 100 if tot else 0)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(counts, reductions, color='#9C27B0', linewidth=2.5,
            marker='o', markersize=8, markerfacecolor='white', markeredgewidth=2)
    ax.fill_between(counts, reductions, alpha=0.15, color='#9C27B0')
    ax.set_xlabel('Number of patterns in NFA')
    ax.set_ylabel('Average pruning ratio (%)')
    ax.set_title('Fig 3 — Pruning Ratio vs Pattern Count  (HTTP input, W=32)')
    ax.set_ylim(0, 60)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))
    ax.grid(True, alpha=0.3, linestyle='--')

    plt.tight_layout()
    plt.savefig('figures/fig3_pattern_count.png', dpi=150, bbox_inches='tight')
    plt.close()
    print('  saved figures/fig3_pattern_count.png')


def fig4():
    W      = 32
    n_show = 500

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=False)

    for ax, data, title, color in [
        (ax1, gen_http(20)[:n_show],  'HTTP traffic', '#2196F3'),
        (ax2, gen_binary(n_show),     'Binary data',  '#F44336'),
    ]:
        win    = WindowProfiler(W)
        sizes  = []
        for byte in data[:n_show]:
            win.update(byte)
            sizes.append(len(win.allowed))

        xs = list(range(len(sizes)))
        ax.plot(xs, sizes, color=color, linewidth=1.5, alpha=0.9)
        ax.fill_between(xs, sizes, alpha=0.2, color=color)
        avg = sum(sizes) / len(sizes)
        ax.axhline(256, color='gray', linestyle='--', linewidth=1,
                   alpha=0.5, label='Full alphabet (256)')
        ax.axhline(avg, color=color, linestyle=':', linewidth=1.5,
                   label=f'Average: {avg:.0f}')
        ax.set_ylabel("|Σ′| (active chars)")
        ax.set_title(title)
        ax.set_ylim(0, 270)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.2, linestyle='--')

    ax2.set_xlabel('Stream position (bytes)')
    fig.suptitle(f'Fig 4 — Live |Σ′| Over Stream  (W={W})', fontweight='bold')
    plt.tight_layout()
    plt.savefig('figures/fig4_stream_profile.png', dpi=150, bbox_inches='tight')
    plt.close()
    print('  saved figures/fig4_stream_profile.png')

def fig5():
    nfa = MultiPatternNFA(PATTERNS)
    ws  = [4, 8, 16, 32, 64, 128]

    configs = [
        ('HTTP + GET/POST',   gen_http(40)),
        ('HTTP + patterns',   gen_http(40)),
        ('DNS + QUERY',       gen_dns(100)),
        ('JSON data',         gen_json(50)),
        ('Binary + patterns', gen_binary(5000)),
        ('Mixed + all',       gen_mixed(10000)),
    ]

    matrix = np.zeros((len(configs), len(ws)))
    for i, (_, data) in enumerate(configs):
        for j, W in enumerate(ws):
            win = WindowProfiler(W)
            std = nfa.run_standard(data)
            prn = nfa.run_pruned(data, window=win)
            matrix[i][j] = 1.0 if std['matches'] == prn['matches'] else 0.0

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.imshow(matrix, cmap='RdYlGn', vmin=0, vmax=1, aspect='auto')

    ax.set_xticks(range(len(ws)))
    ax.set_xticklabels([f'W={w}' for w in ws])
    ax.set_yticks(range(len(configs)))
    ax.set_yticklabels([c[0] for c in configs])

    for i in range(len(configs)):
        for j in range(len(ws)):
            ax.text(j, i, 'PASS' if matrix[i][j] == 1 else 'FAIL',
                    ha='center', va='center', fontsize=9,
                    fontweight='bold', color='white')

    ax.set_title('Fig 5 — Correctness: Pruned vs Standard Engine')
    plt.tight_layout()
    plt.savefig('figures/fig5_correctness.png', dpi=150, bbox_inches='tight')
    plt.close()
    print('  saved figures/fig5_correctness.png')


if __name__ == '__main__':
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()

