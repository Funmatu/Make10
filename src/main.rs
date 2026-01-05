use std::env;
use std::fs::File;
use std::io::{self, BufRead, BufReader};
use std::hint::black_box;

// 同じクレート内のライブラリ部分を利用
use make10::solve_native;

fn main() -> io::Result<()> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: {} <input_file>", args[0]);
        return Ok(());
    }
    let filename = &args[1];
    let file = File::open(filename)?;
    
    // 高速化のためバッファサイズを大きく取る
    let mut reader = BufReader::with_capacity(64 * 1024, file);
    let mut line = String::with_capacity(32);

    while reader.read_line(&mut line)? > 0 {
        let trimmed = line.trim();
        if trimmed.len() >= 4 {
            let b = trimmed.as_bytes();
            // 入力がASCII数字であると仮定した高速変換 ('0' = 48)
            let n1 = b[0].wrapping_sub(b'0');
            let n2 = b[1].wrapping_sub(b'0');
            let n3 = b[2].wrapping_sub(b'0');
            let n4 = b[3].wrapping_sub(b'0');
            
            let res = solve_native(n1, n2, n3, n4);
            
            // 最適化による削除を防ぐ
            black_box(res);
        }
        line.clear();
    }
    Ok(())
}