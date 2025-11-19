#!/bin/bash

# エラー時にスクリプトを終了する
set -e

# 必要なパッケージのインストール
echo "🚀 Setting up the project environment..."
apt-get update
apt-get install -y screen vim locales
echo "🎉 Environment setup complete."

# ロケールの設定
echo "🚀 ロケールを設定中..."
locale-gen en_US.UTF-8
update-locale LANG=en_US.UTF-8
echo "🎉 ロケールの設定が完了しました。"

# shellの設定
touch ~/.screenrc
touch ~/.vimrc

# dotファイルの内容を書き込むスクリプトを呼び出す
chmod +x /workspace/setup/shell/write_rc.sh
/workspace/setup/shell/write_rc.sh bashrc
/workspace/setup/shell/write_rc.sh screenrc
/workspace/setup/shell/write_rc.sh vimrc
echo "🎉 Configuration files have been set up."

# uvのインストール
echo "🚀 Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
echo "🎉 uv installation complete."


# Hugging Face CLIのインストール
echo "🚀 Installing Hugging Face CLI..."
pip install --upgrade pip
pip install huggingface_hub hf_transfer
echo "🎉 Hugging Face CLI installation complete."

# Hugging Faceの認証
echo "🚀 Authenticating Hugging Face CLI..."
source ~/.bashrc
FILE_NAME="/workspace/setup/download/.hf_token"
HUGGINGFACE_TOKEN=$(cat $FILE_NAME)
hf auth login --token $HUGGINGFACE_TOKEN --add-to-git-credential
echo 'export HF_TOKEN=$HUGGINGFACE_TOKEN' >> ~/.bashrc
echo "🎉 Hugging Face CLI authenticated."

# ディレクトリの作成
echo "🚀 Creating project directories..."
cd /workspace
if [ -e "dataset" ] || [ -e "projects" ]; then
    echo "⚠️ 'dataset' or 'projects' directory already exists. Skipping creation."
    exit 0
fi
mkdir dataset
mkdir projects
echo "🎉 Project directories created."