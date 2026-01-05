// 自動生成されたテーブルモジュールを読み込み
pub mod generated_table;
use generated_table::SOLUTIONS;

#[cfg(feature = "python")]
use std::sync::{Mutex, OnceLock};
#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::types::PyTuple;

#[cfg(feature = "wasm")]
use wasm_bindgen::prelude::*;

// -----------------------------------------------------------------------------
// Core Logic
// -----------------------------------------------------------------------------

/// インデックス計算 (Perfect Hashing)
/// ソートネットワーク (N=4) を使用して比較・交換コストを最小化
#[inline(always)]
pub fn get_index(n1: u8, n2: u8, n3: u8, n4: u8) -> Option<usize> {
    // ASCII数字入力を想定した場合の安全策（不要なら削除可）
    if n1 > 9 || n2 > 9 || n3 > 9 || n4 > 9 {
        return None;
    }

    let (mut a, mut b, mut c, mut d) = (n1, n2, n3, n4);

    // Sorting Network for 4 elements
    if a > b { std::mem::swap(&mut a, &mut b); }
    if c > d { std::mem::swap(&mut c, &mut d); }
    if a > c { std::mem::swap(&mut a, &mut c); }
    if b > d { std::mem::swap(&mut b, &mut d); }
    if b > c { std::mem::swap(&mut b, &mut c); }

    Some((a as usize) * 1000 + (b as usize) * 100 + (c as usize) * 10 + (d as usize))
}

/// Rustネイティブ用の解決関数（CLI等から利用）
/// 最適化で消されないよう black_box を含めるかは呼び出し元次第だが、ここでは値を返す。
#[inline(always)]
pub fn solve_native(n1: u8, n2: u8, n3: u8, n4: u8) -> &'static [&'static str] {
    if let Some(idx) = get_index(n1, n2, n3, n4) {
        SOLUTIONS[idx]
    } else {
        &[]
    }
}

// -----------------------------------------------------------------------------
// Python Interface
// -----------------------------------------------------------------------------

#[cfg(feature = "python")]
static PY_CACHE: OnceLock<Mutex<Vec<Option<Py<PyTuple>>>>> = OnceLock::new();

#[cfg(feature = "python")]
#[pyfunction]
fn solve(py: Python, n1: u8, n2: u8, n3: u8, n4: u8) -> PyResult<Py<PyTuple>> {
    let idx = match get_index(n1, n2, n3, n4) {
        Some(i) => i,
        None => return Ok(PyTuple::empty(py).into()),
    };

    let cache_mutex = PY_CACHE.get_or_init(|| {
        Mutex::new(vec![None; 10000])
    });

    let mut cache = cache_mutex.lock().unwrap();

    if let Some(ref cached_obj) = cache[idx] {
        return Ok(cached_obj.clone_ref(py));
    }

    let solution_strs = SOLUTIONS[idx];
    let py_tuple = PyTuple::new(py, solution_strs);
    let py_obj: Py<PyTuple> = py_tuple.into();

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
// WebAssembly Interface
// -----------------------------------------------------------------------------

#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn solve_js(n1: u8, n2: u8, n3: u8, n4: u8) -> Result<JsValue, JsValue> {
    let results = solve_native(n1, n2, n3, n4);
    Ok(serde_wasm_bindgen::to_value(results)?)
}