import timeit
import itertools

# Python版ソルバー(事前に生成したmake10_table_all.py)をインポート
try:
    from make10_table_all import SOLUTIONS as PY_SOLUTIONS
except ImportError:
    print("Warning: make10_table_all.py not found. Python benchmark will fail.")
    PY_SOLUTIONS = {}

# Rust版モジュール
try:
    import make10
except ImportError:
    print("Error: Rust module 'make10' not installed. Run 'maturin develop' first.")
    exit(1)


def bench_python(n1, n2, n3, n4):
    key = tuple(sorted((n1, n2, n3, n4)))
    return PY_SOLUTIONS.get(key, [])


def bench_rust(n1, n2, n3, n4):
    return make10.solve(n1, n2, n3, n4)


def run_benchmark():
    test_inputs = [
        (1, 4, 5, 7),  # 解あり
        (0, 0, 0, 0),  # 解なし
        (9, 9, 9, 9),  # 解あり
        (3, 4, 7, 8),  # 解あり
    ]

    print(f"{'Input':<15} | {'Python (µs)':<12} | {'Rust (µs)':<12} | {'Speedup':<8}")
    print("-" * 55)

    for nums in test_inputs:
        # Python
        t_py = timeit.timeit(lambda: bench_python(*nums), number=100000)
        t_py_avg = (t_py / 100000) * 1_000_000

        # Rust
        t_rs = timeit.timeit(lambda: bench_rust(*nums), number=100000)
        t_rs_avg = (t_rs / 100000) * 1_000_000

        speedup = t_py_avg / t_rs_avg if t_rs_avg > 0 else 0.0

        print(
            f"{str(nums):<15} | {t_py_avg:12.3f} | {t_rs_avg:12.3f} | {speedup:7.1f}x"
        )


if __name__ == "__main__":
    print("Running Benchmark: Python Dict Lookup vs Rust Static Array via PyO3")
    run_benchmark()
