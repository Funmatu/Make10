import itertools
from fractions import Fraction
import sys

# --- 設定 ---
OPS = [
    (lambda x, y: x + y, "+"),
    (lambda x, y: x - y, "-"),
    (lambda x, y: x * y, "*"),
    (lambda x, y: None if y == 0 else x / y, "/"),
]


def get_all_solutions(nums):
    """
    4つの数字に対する全ての解を探索し、文字列のリストとして返す。
    Rust版のロジックを再現。
    """
    found_exprs = set()
    unique_permutations = set(itertools.permutations(nums))

    for p in unique_permutations:
        a, b, c, d = [Fraction(x) for x in p]

        for op1, op2, op3 in itertools.product(OPS, repeat=3):
            f1, s1 = op1
            f2, s2 = op2
            f3, s3 = op3

            # Pattern 1: ((A op B) op C) op D
            try:
                r1 = f1(a, b)
                if r1 is not None:
                    r2 = f2(r1, c)
                    if r2 is not None:
                        res = f3(r2, d)
                        if res is not None and res == 10:
                            found_exprs.add(f"(({p[0]}{s1}{p[1]}){s2}{p[2]}){s3}{p[3]}")
            except:
                pass

            # Pattern 2: (A op B) op (C op D)
            try:
                rl = f1(a, b)
                rr = f2(c, d)
                if rl is not None and rr is not None:
                    res = f3(rl, rr)
                    if res is not None and res == 10:
                        found_exprs.add(f"({p[0]}{s1}{p[1]}){s3}({p[2]}{s2}{p[3]})")
            except:
                pass

    # ソートしてリスト化（見た目を整えるため）
    return sorted(list(found_exprs))


def generate_mawk_source():
    print("Generating Mawk Code (Lookup Table)...", file=sys.stderr)

    awk_lines = []

    # --- Header ---
    awk_lines.append("BEGIN {")
    awk_lines.append('    FS = "" # 入力自動分解')
    awk_lines.append('    OFS = ", " # 出力区切り文字')
    awk_lines.append("")

    # --- Table Generation ---
    combinations = list(itertools.combinations_with_replacement(range(10), 4))
    count = 0
    mapped_count = 0

    for combo in combinations:
        # キー生成 (Sorted Tuple -> Integer)
        # 1,4,5,7 -> 1457
        key_tuple = sorted(combo)
        idx = (
            key_tuple[0] * 1000 + key_tuple[1] * 100 + key_tuple[2] * 10 + key_tuple[3]
        )

        solutions = get_all_solutions(combo)
        if solutions:
            # 配列代入文字列の作成
            # mawkは文字列連結が速いが、ソースコードが大きくなりすぎないよう配慮
            # 解をカンマ区切りの1つの文字列として格納する
            joined_sols = ", ".join(solutions)
            awk_lines.append(f'    S[{idx}] = "{joined_sols}"')
            mapped_count += 1
        count += 1

    print(
        f"Generated {mapped_count} patterns out of {count} combinations.",
        file=sys.stderr,
    )

    awk_lines.append("}")
    awk_lines.append("")

    # --- Main Loop (Processing) ---
    awk_lines.append("{")
    awk_lines.append("    if (NF < 4) next")
    awk_lines.append("")
    awk_lines.append("    # --- 1. Load & Cast ---")
    awk_lines.append("    n1 = $1 + 0; n2 = $2 + 0; n3 = $3 + 0; n4 = $4 + 0")
    awk_lines.append("")
    awk_lines.append("    # --- 2. Sorting Network (N=4) ---")
    awk_lines.append("    # ループなしで正規化キーを作成するためのソート")
    awk_lines.append("    if (n1 > n2) { t=n1; n1=n2; n2=t }")
    awk_lines.append("    if (n3 > n4) { t=n3; n3=n4; n4=t }")
    awk_lines.append("    if (n1 > n3) { t=n1; n1=n3; n3=t }")
    awk_lines.append("    if (n2 > n4) { t=n2; n2=n4; n4=t }")
    awk_lines.append("    if (n2 > n3) { t=n2; n2=n3; n3=t }")
    awk_lines.append("")
    awk_lines.append("    # --- 3. Key Calculation & Lookup ---")
    awk_lines.append("    key = n1*1000 + n2*100 + n3*10 + n4")
    awk_lines.append("")
    awk_lines.append("    if (key in S) {")
    awk_lines.append('        print $0 " -> [" S[key] "]"')
    awk_lines.append("    } else {")
    awk_lines.append('        print $0 " -> []"')
    awk_lines.append("    }")
    awk_lines.append("}")

    return "\n".join(awk_lines)


if __name__ == "__main__":
    src = generate_mawk_source()
    with open("scripts/make10_ultimate.awk", "w", encoding="utf-8") as f:
        f.write(src)
    print("Done: make10_ultimate.awk generated.")
