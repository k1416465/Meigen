import sqlite3
import shutil
from pathlib import Path

# このプログラムと同じフォルダーにDBを置く
db_path = Path(__file__).with_name("recordings.db")

if not db_path.exists():
    print("recordings.db が見つかりません。")
    print("このプログラムをDBと同じフォルダーに置いてください。")
    input("Enterキーで終了")
    raise SystemExit

# 元のDBをバックアップ（初回のみ）
backup_path = db_path.with_name("recordings_backup.db")
if not backup_path.exists():
    shutil.copy2(db_path, backup_path)
    print("バックアップを作成しました:", backup_path.name)

with sqlite3.connect(db_path) as conn:
    rows = conn.execute(
        "SELECT id, filename, title, tags FROM recordings ORDER BY id"
    ).fetchall()

    print("\n=== 録音一覧 ===")
    for rec_id, filename, title, tags in rows:
        print(f"\nID: {rec_id}")
        print(f"ファイル: {filename}")
        print(f"タイトル: {title}")
        print(f"現在のタグ: {tags}")

    try:
        rec_id = int(input("\nタグを追加する録音のID: "))
    except ValueError:
        print("IDは数字で入力してください。")
        input("Enterキーで終了")
        raise SystemExit

    row = conn.execute(
        "SELECT tags FROM recordings WHERE id = ?", (rec_id,)
    ).fetchone()

    if row is None:
        print("そのIDの録音は見つかりません。")
    else:
        old_tags = row[0] or ""
        tag = input("追加するタグ: ").strip()

        if not tag:
            print("タグが空なので変更しません。")
        else:
            # カンマ区切りで保存し、重複追加を防ぐ
            existing = [t.strip() for t in old_tags.split(",") if t.strip()]

            if tag in existing:
                print("そのタグはすでに登録されています。")
            else:
                new_tags = ",".join(existing + [tag])
                conn.execute(
                    "UPDATE recordings SET tags = ? WHERE id = ?",
                    (new_tags, rec_id)
                )
                conn.commit()
                print("タグを追加しました:", new_tags)

input("\nEnterキーで終了")