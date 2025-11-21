#!/bin/bash

# Hugging Face token の場所
TOKEN_FILE="/workspace/setup/download/.hf_token"

echo "🔍 Checking Hugging Face token..."

# すでに環境変数 HF_TOKEN がある場合
if [ -n "$HF_TOKEN" ]; then
    echo "✅ Environment variable HF_TOKEN is already set."
    echo "HF_TOKEN=${HF_TOKEN}"
else
    echo "⚠️ Environment variable HF_TOKEN not found."

    # ファイルが存在するか？
    if [ -f "$TOKEN_FILE" ]; then
        echo "📄 Token file found: $TOKEN_FILE"
        export HF_TOKEN=$(cat "$TOKEN_FILE")
        echo "🔧 HF_TOKEN has been set from file."
    else
        echo "❌ ERROR: Neither HF_TOKEN environment variable nor token file found."
        echo "Please set HF_TOKEN manually or create $TOKEN_FILE"
        exit 1
    fi
fi
echo "export HF_TOKEN=${HF_TOKEN}" >> ~/.bashrc
echo "🎉 HF_TOKEN is ready to use."

screen -S download_imagenet1k -dm python /workspace/setup/download/imagenet1k.py