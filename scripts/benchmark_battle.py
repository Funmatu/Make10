import sys
import os
import time
import timeit
import itertools
import subprocess
import random
from fractions import Fraction

# ==========================================
# 設定 & 定数
# ==========================================
SCRIPT_DIR = "."  # カレントディレクトリで実行
DATA_FILE = os.path.join(SCRIPT_DIR, "scripts/benchmark_data.txt")
AWK_FILE = os.path.join(SCRIPT_DIR, "scripts/make10_ultimate.awk")
RUST_BIN_PATH = os.path.join(
    SCRIPT_DIR, "target/release/make10_cli"
)  # CLIバイナリのパス
# PyO3モジュールはPythonのsys.pathに追加されることを期待

# ベンチマーク設定
NUM_RECORDS = 1_000_000  # 100万行
CHUNK_SIZE = 100_000

# ==========================================
# 0. 環境準備 (事前チェック)
# ==========================================
print(f"[{'SETUP':^10}] Checking prerequisites...")

# Rust CLIバイナリの存在確認
RUST_BIN_AVAILABLE = os.path.exists(RUST_BIN_PATH)
if not RUST_BIN_AVAILABLE:
    print(
        f"  -> Warning: Rust native binary not found at '{RUST_BIN_PATH}'. Rust native benchmark will be skipped."
    )
    print("     Please run `cargo build --release --bin make10_cli` first.")

# PyO3モジュールの存在確認
try:
    import make10

    RUST_PY_AVAILABLE = True
    print("  -> Rust PyO3 module 'make10' imported successfully.")
except ImportError:
    RUST_PY_AVAILABLE = False
    print(
        "  -> Warning: Rust PyO3 module 'make10' not found. Rust via Python benchmark will be skipped."
    )
    print("     Please run `maturin develop --release --features python` first.")

# AWKスクリプトの存在確認
AWK_SCRIPT_AVAILABLE = os.path.exists(AWK_FILE)
if not AWK_SCRIPT_AVAILABLE:
    print(
        f"  -> Warning: AWK script not found at '{AWK_FILE}'. AWK benchmark will be skipped."
    )
    print("     Please run `python tools/make_make10_ultimate_awk.py` to generate it.")

# ==========================================
# 1. コアロジック: Make10ソルバー (Python & Data Gen)
# ==========================================
print(f"[{'SETUP':^10}] Initializing Make10 Logic & Generating Python Data Table...")

OPS = [
    (lambda x, y: x + y, "+"),
    (lambda x, y: x - y, "-"),
    (lambda x, y: x * y, "*"),
    (lambda x, y: None if y == 0 else x / y, "/"),
]


def solve_expression(nums):
    solutions = set()
    for p in set(itertools.permutations(nums)):
        a, b, c, d = [Fraction(x) for x in p]
        for op1, op2, op3 in itertools.product(OPS, repeat=3):
            f1, s1 = op1
            f2, s2 = op2
            f3, s3 = op3
            try:
                r1 = f1(a, b)
                if r1 is not None:
                    r2 = f2(r1, c)
                    if r2 is not None:
                        res = f3(r2, d)
                        if res is not None and res == 10:
                            solutions.add(f"(({p[0]}{s1}{p[1]}){s2}{p[2]}){s3}{p[3]}")
            except (
                TypeError,
                ZeroDivisionError,
            ):  # Python 3.9+ handles ZeroDivisionError in Fraction division
                pass
            try:
                rl = f1(a, b)
                rr = f2(c, d)
                if rl is not None and rr is not None:
                    res = f3(rl, rr)
                    if res is not None and res == 10:
                        solutions.add(f"({p[0]}{s1}{p[1]}){s3}({p[2]}{s2}{p[3]})")
            except (TypeError, ZeroDivisionError):
                pass
    return sorted(list(solutions))


# 全パターン計算とPythonテーブルデータの準備
start_gen = time.time()
PY_TABLE = {}
count_solved = 0

combinations = list(itertools.combinations_with_replacement(range(10), 4))

for combo in combinations:
    key_tuple = tuple(sorted(combo))  # sorted tuple for dictionary key
    sols = solve_expression(combo)
    PY_TABLE[key_tuple] = sols

    if sols:
        count_solved += 1

print(
    f"[{'DONE':^10}] Generated Python solution table ({count_solved} solvable patterns) in {time.time() - start_gen:.3f} sec."
)

# ==========================================
# 2. テストデータ生成
# ==========================================
print(f"[{'SETUP':^10}] Generating {NUM_RECORDS:,} test records...")
with open(DATA_FILE, "w") as f:
    for _ in range(0, NUM_RECORDS, CHUNK_SIZE):
        lines = [f"{random.randint(0, 9999):04d}" for _ in range(CHUNK_SIZE)]
        f.write("\n".join(lines) + "\n")

# ==========================================
# 3. ベンチマーク実行: Round 1 (Latency)
# ==========================================
print("\n" + "=" * 80)
print(f"{'ROUND 1: LATENCY (Overhead Check)':^80}")
print("=" * 80)
print("Measure: Time to solve ONE input (Microseconds)")
print("  - Python/Rust(Py): Function call overhead")
print("  - Mawk: Process spawn + Compilation + Execution overhead (if available)")
print("-" * 80)

# Mawkコマンド決定
awk_cmd = "mawk"
if (
    subprocess.call(
        ["which", "mawk"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    != 0
):
    awk_cmd = "awk"
    if (
        subprocess.call(
            ["which", "awk"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        != 0
    ):
        print(
            "  -> Warning: Neither 'mawk' nor 'awk' found. AWK latency benchmark will be skipped."
        )
        AWK_SCRIPT_AVAILABLE = False  # AWK実行不可とする


def bench_py(n1, n2, n3, n4):
    k = tuple(sorted((n1, n2, n3, n4)))
    return PY_TABLE.get(k)


def bench_rs_py(n1, n2, n3, n4):
    if RUST_PY_AVAILABLE:
        return make10.solve(n1, n2, n3, n4)
    return []


def bench_mawk_proc(n1, n2, n3, n4):
    if AWK_SCRIPT_AVAILABLE:
        inp = f"{n1}{n2}{n3}{n4}\n".encode()
        # stdoutはDEVNULLに捨てる。AWK_FILEがOFSで出力するので、そこは変更しない。
        subprocess.run(
            [awk_cmd, "-f", AWK_FILE],
            input=inp,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


test_inputs = [(1, 4, 5, 7), (9, 9, 9, 9)]
print(
    f"{'Input':<15} | {'Python (µs)':>12} | {'Rust(Py) (µs)':>12} | {'Mawk (µs)':>12}"
)

for nums in test_inputs:
    # Python
    t_py = timeit.timeit(lambda: bench_py(*nums), number=50000) * 1_000_000 / 50000

    # Rust via Python
    if RUST_PY_AVAILABLE:
        t_rs = (
            timeit.timeit(lambda: bench_rs_py(*nums), number=50000) * 1_000_000 / 50000
        )
        rs_str = f"{t_rs:.3f}"
    else:
        rs_str = "-"

    # Mawk (Process) - 遅いので回数減らす
    awk_str = "-"
    if AWK_SCRIPT_AVAILABLE:
        t_awk_start = time.time()
        for _ in range(20):
            bench_mawk_proc(*nums)
        t_awk = (time.time() - t_awk_start) * 1_000_000 / 20
        awk_str = f"{t_awk:.3f}"

    print(f"{str(nums):<15} | {t_py:12.3f} | {rs_str:>12} | {awk_str:>12}")

print("-" * 80)

# ==========================================
# 4. ベンチマーク実行: Round 2 (Throughput)
# ==========================================
print("\n" + "=" * 80)
print(f"{'ROUND 2: THROUGHPUT (File I/O + Process)':^80}")
print("=" * 80)
print(f"Measure: Total time to process {NUM_RECORDS:,} lines.")
print("Goal: Compare pure processing power including I/O strategies.")
print("-" * 80)

results = []

# --- Python ---
print("1. Running Python (Pure)...", end="", flush=True)
start = time.time()
with open(DATA_FILE, "r") as f:
    for line in f:
        l = line.strip()
        if len(l) < 4:
            continue
        n1, n2, n3, n4 = int(l[0]), int(l[1]), int(l[2]), int(l[3])
        _ = PY_TABLE.get(tuple(sorted((n1, n2, n3, n4))))
dur_py = time.time() - start
results.append(("Python (Pure)", dur_py))
print(
    f"\r1. Python (Pure)        : {dur_py:.4f} s ({int(NUM_RECORDS / dur_py):,} ops/s)"
)

# --- Rust via Python ---
if RUST_PY_AVAILABLE:
    print("2. Running Rust (via Py)...", end="", flush=True)
    start = time.time()
    with open(DATA_FILE, "r") as f:
        for line in f:
            l = line.strip()
            if len(l) < 4:
                continue
            n1, n2, n3, n4 = int(l[0]), int(l[1]), int(l[2]), int(l[3])
            _ = make10.solve(n1, n2, n3, n4)
    dur_rs_py = time.time() - start
    results.append(("Rust (via Py)", dur_rs_py))
    print(
        f"\r2. Rust (via Py)        : {dur_rs_py:.4f} s ({int(NUM_RECORDS / dur_rs_py):,} ops/s)"
    )

# --- Mawk ---
if AWK_SCRIPT_AVAILABLE:
    print(f"3. Running {awk_cmd} (Native)...", end="", flush=True)
    start = time.time()
    # stdoutをDEVNULLに捨てることで、ターミナル表示速度ではなく計算速度を測る
    subprocess.run(
        [awk_cmd, "-f", AWK_FILE, DATA_FILE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    dur_awk = time.time() - start
    results.append((f"{awk_cmd} (Native)", dur_awk))
    print(
        f"\r3. {awk_cmd:<18} : {dur_awk:.4f} s ({int(NUM_RECORDS / dur_awk):,} ops/s)"
    )

# --- Rust Native Binary ---
if RUST_BIN_AVAILABLE:
    print("4. Running Rust (Native Binary)...", end="", flush=True)
    start = time.time()
    subprocess.run(
        [RUST_BIN_PATH, DATA_FILE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    dur_rs_bin = time.time() - start
    results.append(("Rust (Native Binary)", dur_rs_bin))
    print(
        f"\r4. Rust (Native Binary) : {dur_rs_bin:.4f} s ({int(NUM_RECORDS / dur_rs_bin):,} ops/s)"
    )

# ==========================================
# 最終結果表示
# ==========================================
print("\n" + "=" * 80)
print(f"{'FINAL SUMMARY':^80}")
print("=" * 80)
results.sort(key=lambda x: x[1])

print(f"{'Rank':<4} | {'Name':<22} | {'Time (sec)':<10} | {'Throughput':<15} | {'Rel'}")
print("-" * 80)
if results:
    best_time = results[0][1]
    for i, (name, dur) in enumerate(results, 1):
        throughput = f"{int(NUM_RECORDS / dur):,} ops/s"
        rel = f"{dur / best_time:.2f}x"
        print(f"{i:<4} | {name:<22} | {dur:10.4f} | {throughput:<15} | {rel}")
else:
    print("No benchmarks ran.")
print("=" * 80)
