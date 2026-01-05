import init, { solve_js } from './pkg/make10.js';

async function main() {
    // WASMモジュールの初期化
    await init();

    const btn = document.getElementById('solve-btn');
    const output = document.getElementById('output');
    const inputs = [
        document.getElementById('n1'),
        document.getElementById('n2'),
        document.getElementById('n3'),
        document.getElementById('n4')
    ];

    btn.innerText = "Solve (Find All Solutions)";
    btn.disabled = false;

    // 入力欄でEnterキーを押しても実行
    inputs.forEach(input => {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') btn.click();
        });
    });

    btn.addEventListener('click', () => {
        // 値の取得
        const nums = inputs.map(el => parseInt(el.value) || 0);
        
        // --- Benchmark Start ---
        const start = performance.now();
        
        // Rust関数の呼び出し (O(1) Lookup)
        const solutions = solve_js(...nums);
        
        const end = performance.now();
        // --- Benchmark End ---

        const timeMs = (end - start).toFixed(3);

        // 結果のレンダリング
        if (solutions.length === 0) {
            output.innerHTML = `
                <div class="stat-card">Execution Time: ${timeMs} ms</div>
                <div class="no-solution">No solution found for [${nums.join(', ')}]</div>
            `;
        } else {
            const listHtml = solutions.map(s => `<div class="solution-item">${s} = 10</div>`).join('');
            output.innerHTML = `
                <div class="stat-card">
                    Found ${solutions.length} solutions in ${timeMs} ms<br>
                    (Sorted & Deduped)
                </div>
                <div class="solution-grid">${listHtml}</div>
            `;
        }
    });
}

main().catch(console.error);