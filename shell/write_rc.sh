#!/bin/bash

# エラー時にスクリプトを終了する
set -e

# dot.screenrc ファイルのパスを指定
SOURCE_FILE="/workspace/setup/shell/shell_settings/dot.$1"

# ~/.screenrc のパス
TARGET_FILE="$HOME/.$1"

# dot.screenrc が存在しない場合はエラーを表示して終了
if [ ! -f "$SOURCE_FILE" ]; then
    echo "Error: File '$SOURCE_FILE' not found."
    exit 1
fi

# dot.screenrc の内容を ~/.screenrc に書き込む
cat "$SOURCE_FILE" > "$TARGET_FILE"

# 完了メッセージ
echo "🎉 Content of '$SOURCE_FILE' has been written to '$TARGET_FILE'."