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
DATA_FILE = "scripts/benchmark_data.txt"
AWK_FILE = "scripts/make10_ultimate.awk"
NUM_RECORDS = 1_000_000  # 100万行
RUST_MODULE_NAME = "make10"

# ==========================================
# 1. コアロジック: Make10ソルバー (Python版)
# ==========================================
print(f"[{'SETUP':^10}] Initializing Make10 Solver Logic...")

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
            except:
                pass
            try:
                rl = f1(a, b)
                rr = f2(c, d)
                if rl is not None and rr is not None:
                    res = f3(rl, rr)
                    if res is not None and res == 10:
                        solutions.add(f"({p[0]}{s1}{p[1]}){s3}({p[2]}{s2}{p[3]})")
            except:
                pass
    return sorted(list(solutions))


# ==========================================
# 2. ルックアップテーブルの全生成
# ==========================================
print(f"[{'SETUP':^10}] Pre-calculating ALL 715 patterns (Python)...")
start_gen = time.time()

PY_TABLE = {}
AWK_DATA_LINES = []
combinations = list(itertools.combinations_with_replacement(range(10), 4))

for combo in combinations:
    key_tuple = tuple(sorted(combo))
    sols = solve_expression(combo)
    PY_TABLE[key_tuple] = sols
    idx = key_tuple[0] * 1000 + key_tuple[1] * 100 + key_tuple[2] * 10 + key_tuple[3]
    if sols:
        sol_str = ", ".join(sols).replace('"', '\\"')
        AWK_DATA_LINES.append(f'    S[{idx}] = "{sol_str}"')

gen_time = time.time() - start_gen
print(f"[{'DONE':^10}] Generated {len(combinations)} entries in {gen_time:.3f} sec.")

# ==========================================
# 3. 完全な AWK スクリプトの生成
# ==========================================
print(f"[{'SETUP':^10}] Writing '{AWK_FILE}' (Full Lookup Table)...")

awk_script_content = """BEGIN {
    FS = ""
    OFS = " -> "
"""
awk_script_content += "\n".join(AWK_DATA_LINES)
awk_script_content += """
}
{
    if (NF < 4) next
    n1 = $1 + 0; n2 = $2 + 0; n3 = $3 + 0; n4 = $4 + 0
    if (n1 > n2) { t=n1; n1=n2; n2=t }
    if (n3 > n4) { t=n3; n3=n4; n4=t }
    if (n1 > n3) { t=n1; n1=n3; n3=t }
    if (n2 > n4) { t=n2; n2=n4; n4=t }
    if (n2 > n3) { t=n2; n2=n3; n3=t }
    key = n1*1000 + n2*100 + n3*10 + n4
    if (key in S) { found = 1 } else { found = 0 }
}
"""
with open(AWK_FILE, "w", encoding="utf-8") as f:
    f.write(awk_script_content)

# ==========================================
# 4. テストデータの生成
# ==========================================
print(f"[{'SETUP':^10}] Generating {NUM_RECORDS:,} test records to '{DATA_FILE}'...")
with open(DATA_FILE, "w") as f:
    chunk_size = 100_000
    for _ in range(0, NUM_RECORDS, chunk_size):
        lines = [f"{random.randint(0, 9999):04d}" for _ in range(chunk_size)]
        f.write("\n".join(lines) + "\n")

# ==========================================
# 5. Rustモジュールのロード確認
# ==========================================
try:
    import make10

    RUST_AVAILABLE = True
    print(f"[{'INFO':^10}] Rust module '{RUST_MODULE_NAME}' loaded successfully.")
except ImportError:
    RUST_AVAILABLE = False
    print(f"[{'WARN':^10}] Rust module '{RUST_MODULE_NAME}' NOT found (skipping Rust).")

# ==========================================
# 6. ベンチマーク関数
# ==========================================
# mawkコマンドの特定
awk_cmd = "mawk"
if subprocess.call(["which", "mawk"], stdout=subprocess.DEVNULL) != 0:
    awk_cmd = "awk"


def bench_python_lookup(n1, n2, n3, n4):
    key = tuple(sorted((n1, n2, n3, n4)))
    return PY_TABLE.get(key, [])


def bench_rust_lookup(n1, n2, n3, n4):
    if RUST_AVAILABLE:
        return make10.solve(n1, n2, n3, n4)
    return []


def bench_mawk_single(n1, n2, n3, n4):
    """
    1回だけMawkプロセスを起動して解かせる。
    プロセス起動コスト + スクリプトパースコスト + 実行コスト の合計になる。
    """
    input_str = f"{n1}{n2}{n3}{n4}\n"
    subprocess.run(
        [awk_cmd, "-f", AWK_FILE],
        input=input_str.encode("utf-8"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ==========================================
# Round 1: Latency (単発呼び出し)
# ==========================================
print("\n" + "=" * 70)
print(f"{'ROUND 1: LATENCY (Single Call Overhead)':^70}")
print("=" * 70)
print("Measure: Time to solve ONE input (Microseconds)")
print("Note: Mawk includes process spawn overhead (Process vs Function call).")
print("-" * 70)
print(f"{'Input':<15} | {'Python (µs)':>12} | {'Rust (µs)':>12} | {'Mawk (µs)':>12}")
print("-" * 70)

test_inputs = [(1, 4, 5, 7), (0, 0, 0, 0), (9, 9, 9, 9)]

for nums in test_inputs:
    # Python (100,000回平均)
    t_py = timeit.timeit(lambda: bench_python_lookup(*nums), number=100000)
    t_py_avg = (t_py / 100000) * 1_000_000

    # Rust (100,000回平均)
    if RUST_AVAILABLE:
        t_rs = timeit.timeit(lambda: bench_rust_lookup(*nums), number=100000)
        t_rs_avg = (t_rs / 100000) * 1_000_000
    else:
        t_rs_avg = 0.0

    # Mawk (100回平均) ※遅すぎるので回数を減らす
    # プロセス起動を含むため、ここが圧倒的に遅くなるはず
    start = time.time()
    for _ in range(100):
        bench_mawk_single(*nums)
    t_awk_total = time.time() - start
    t_awk_avg = (t_awk_total / 100) * 1_000_000

    rs_str = f"{t_rs_avg:12.3f}" if RUST_AVAILABLE else f"{'-':>12}"
    print(f"{str(nums):<15} | {t_py_avg:12.3f} | {rs_str} | {t_awk_avg:12.3f}")

print("-" * 70)
print("Analysis: Mawk is ~10,000x slower here due to process spawning.")
print("-" * 70)


# ==========================================
# Round 2: Throughput (ストリーム処理)
# ==========================================
print("\n" + "=" * 70)
print(f"{'ROUND 2: THROUGHPUT (1,000,000 Records)':^70}")
print("=" * 70)
print("Measure: Total time to process 1,000,000 lines.")
print("-" * 70)

results = []

# --- Python ---
print("Running Python (Pure)...", end="", flush=True)
start = time.time()
with open(DATA_FILE, "r") as f:
    for line in f:
        l = line.strip()
        if len(l) < 4:
            continue
        n1, n2, n3, n4 = int(l[0]), int(l[1]), int(l[2]), int(l[3])
        _ = PY_TABLE.get(tuple(sorted((n1, n2, n3, n4))), [])
dur_py = time.time() - start
results.append(("Python (Pure)", dur_py))
print(f"\rPython (Pure)       : {dur_py:.4f} sec ({NUM_RECORDS / dur_py:,.0f} ops/sec)")

# --- Rust ---
if RUST_AVAILABLE:
    print("Running Rust (via Py)...", end="", flush=True)
    start = time.time()
    with open(DATA_FILE, "r") as f:
        for line in f:
            l = line.strip()
            if len(l) < 4:
                continue
            n1, n2, n3, n4 = int(l[0]), int(l[1]), int(l[2]), int(l[3])
            _ = make10.solve(n1, n2, n3, n4)
    dur_rs = time.time() - start
    results.append(("Rust (via Py)", dur_rs))
    print(
        f"\rRust (via Py)       : {dur_rs:.4f} sec ({NUM_RECORDS / dur_rs:,.0f} ops/sec)"
    )

# --- Mawk ---
print(f"Running {awk_cmd} (Native)...", end="", flush=True)
start = time.time()
subprocess.run([awk_cmd, "-f", AWK_FILE, DATA_FILE], stdout=subprocess.DEVNULL)
dur_awk = time.time() - start
results.append((f"{awk_cmd} (Native)", dur_awk))
print(f"\r{awk_cmd:<20}: {dur_awk:.4f} sec ({NUM_RECORDS / dur_awk:,.0f} ops/sec)")

# ==========================================
# 最終ランキング
# ==========================================
print("\n" + "=" * 70)
print(f"{'FINAL SUMMARY':^70}")
print("=" * 70)
results.sort(key=lambda x: x[1])

print(f"{'Rank':<4} | {'Name':<20} | {'Total Time':<10} | {'Throughput':<15}")
print("-" * 70)
for i, (name, dur) in enumerate(results, 1):
    throughput = f"{NUM_RECORDS / dur:,.0f} ops/s"
    print(f"{i:<4} | {name:<20} | {dur:8.4f} s | {throughput:<15}")
print("=" * 70)
