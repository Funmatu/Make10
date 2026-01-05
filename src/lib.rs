#[cfg(feature = "python")]
use std::sync::{Mutex, OnceLock};

mod generated_table;
use generated_table::SOLUTIONS;

// -----------------------------------------------------------------------------
// Core Logic: The Theoretical Limit
// -----------------------------------------------------------------------------

/// インデックス計算 (Perfect Hashing)
/// 計算量: O(1)
#[inline(always)]
fn get_index(n1: u8, n2: u8, n3: u8, n4: u8) -> Option<usize> {
    if n1 > 9 || n2 > 9 || n3 > 9 || n4 > 9 {
        return None;
    }
    // Tiny sort (sorting network for 4 elements is overkill, standard sort is fine here)
    let mut nums = [n1, n2, n3, n4];
    nums.sort_unstable();
    
    // Calculate unique index: 0000 to 9999
    Some((nums[0] as usize) * 1000 
       + (nums[1] as usize) * 100 
       + (nums[2] as usize) * 10 
       + (nums[3] as usize))
}

// -----------------------------------------------------------------------------
// Python Interface (PyO3) with Zero-Allocation Cache
// -----------------------------------------------------------------------------
#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::types::PyTuple;

/// Pythonオブジェクトのキャッシュ
/// キー: インデックス(0-9999), 値: 生成済みのタプルオブジェクト
/// OnceLockによりスレッドセーフかつ遅延初期化を実現
#[cfg(feature = "python")]
static PY_CACHE: OnceLock<Mutex<Vec<Option<Py<PyTuple>>>>> = OnceLock::new();

#[cfg(feature = "python")]
#[pyfunction]
fn solve(py: Python, n1: u8, n2: u8, n3: u8, n4: u8) -> PyResult<Py<PyTuple>> {
    // 1. Validate & Calc Index
    let idx = match get_index(n1, n2, n3, n4) {
        Some(i) => i,
        None => return Ok(PyTuple::empty(py).into()),
    };

    // 2. Initialize Cache (First time only)
    let cache_mutex = PY_CACHE.get_or_init(|| {
        Mutex::new(vec![None; 10000])
    });

    // 3. Check Cache
    // ロック保持時間は極小。PythonのGILがあるため実質的な競合は稀。
    let mut cache = cache_mutex.lock().unwrap();

    if let Some(ref cached_obj) = cache[idx] {
        // [Cache Hit]
        // 既存オブジェクトのポインタ(参照カウント)を増やすだけ。
        // ヒープ割り当てゼロ、変換コストゼロ。
        return Ok(cached_obj.clone_ref(py));
    }

    // [Cache Miss]
    // 静的データ(&[&str])からPythonタプルを生成
    let solution_strs = SOLUTIONS[idx];
    let py_tuple = PyTuple::new(py, solution_strs);
    let py_obj: Py<PyTuple> = py_tuple.into();

    // キャッシュに保存
    cache[idx] = Some(py_obj.clone_ref(py));

    Ok(py_obj)
}

#[cfg(feature = "python")]
#[pymodule]
fn make10(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(solve, m)?)?;
    Ok(())
}

// -----------------------------------------------------------------------------
// WebAssembly Interface (wasm-bindgen)
// -----------------------------------------------------------------------------
#[cfg(feature = "wasm")]
use wasm_bindgen::prelude::*;

#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn solve_js(n1: u8, n2: u8, n3: u8, n4: u8) -> Result<JsValue, JsValue> {
    let idx = get_index(n1, n2, n3, n4).unwrap_or(0);
    // WASM環境ではJSオブジェクトへの変換が必須なため、キャッシュ戦略は複雑になる。
    // ここではシンプルに毎回シリアライズする(JSエンジン側でGCされるため)。
    let results = SOLUTIONS[idx];
    Ok(serde_wasm_bindgen::to_value(results)?)
}