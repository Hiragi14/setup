"""
データセットのダウンロード、展開、およびその他の共通ユーティリティ関数を提供するヘルパーモジュール。
"""

import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import tarfile
import urllib.request
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import List

import requests
import typer
from huggingface_hub import hf_hub_download
from scipy.io import loadmat
from tqdm import tqdm

# --- 定数 ---
HF_TOKEN = os.getenv("HF_TOKEN" or "")
BASE_DATASET_DIR = Path("../dataset")

logging.basicConfig(
    level=logging.INFO,
    format="\033[31m [%(levelname)s]\033[0m [%(asctime)s] [%(process)d]: [%(filename)s:%(lineno)s] %(funcName)s : %(message)s",
    stream=sys.stdout,
)

log = getLogger(__name__)
app = typer.Typer()


class DiscordWebhook:
    """DiscordのWebhook URLとチャンネルを指定して、メッセージを送信するクラス"""

    def __init__(self, url: str):
        """DiscordのWebhook URLとチャンネルを指定して初期化する。

        Args:
            url (str): DiscordのWebhook URL
            channel (str): メッセージを送信するDiscordのチャンネル名（例: "#general"）
        """
        self.url = url

        self.hostname = socket.gethostname()
        self.icon_emoji = ":desktop_computer:"
        self.current_time = datetime.now().strftime("%Y/%m/%d-%H時%M分")

    def send(self, title: str, message: str, footer: bool = True) -> None:
        """Discordにメッセージを送信する。

        Args:
            title (str): メッセージのタイトル
            message (str): メッセージの内容
            footer (bool): フッターを表示するかどうか
        """
        footer_data = (
            {}
            if not footer
            else {
                "text": self.current_time,
                "icon_url": "https://cdn.discordapp.com/embed/avatars/2.png",
            }
        )
        payload = {
            "username": str(self.hostname),
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": 0x00FF00,
                    "footer": footer_data,
                }
            ],
        }
        response = requests.post(
            self.url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        # エラーが出たらプリント
        if response.status_code == 204:
            log.info("メッセージを送信しました")
        else:
            log.error(f"エラーが発生しました: {response.status_code}")


def run_command(command: List[str]):
    """
    外部コマンドを実行し、エラーハンドリングを行う。

    Args:
        command: 実行するコマンドと引数のリスト。
    """
    try:
        log.info(f"コマンドを実行します: {' '.join(command)}")
        # コマンドの出力をリアルタイムで表示しない場合はPIPEを使い、
        # 表示したい場合はPIPEを外す（ただしエラー時の詳細ログは取得できなくなる）
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        log.error(f"コマンド '{command[0]}' が見つかりません。PATHを確認してください。")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        log.error(f"コマンド実行中にエラーが発生しました: {e}")
        log.error(f"標準出力:\n{e.stdout}")
        log.error(f"標準エラー:\n{e.stderr}")
        sys.exit(1)


def _extract_tar(archive_path: Path, dest_dir: Path, use_pigz: bool = False) -> None:
    """tar.gzファイルを指定されたディレクトリに展開する。

    Args:
        archive_path: 展開するtar.gzファイルのパス。
        dest_dir: 展開先のディレクトリ。
        use_pigz: pigzを使用して展開するかどうかのフラグ。
    """
    log.info(f"{archive_path} を {dest_dir} に展開しています...")
    if use_pigz and shutil.which("pigz"):
        run_command(
            [
                "tar",
                "--use-compress-prog=pigz",
                "-xf",
                str(archive_path),
                "-C",
                str(dest_dir),
            ]
        )
    else:
        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(path=dest_dir)
        except tarfile.TarError as e:
            log.error(f"tarファイルの展開に失敗しました: {e}")
            sys.exit(1)
    log.info("展開が完了しました。")


def organize_imagenet_validation_data(imagenet_dir: Path) -> None:
    """ImageNetの検証用データをDevKitを元にサブディレクトリへ整理する。

    Args:
        imagenet_dir: ImageNetデータセットのルートディレクトリ。
    """
    val_dir = imagenet_dir / "val"
    devkit_dir = imagenet_dir / "ILSVRC2012_devkit_t12"
    meta_path = devkit_dir / "data" / "meta.mat"
    truth_path = devkit_dir / "data" / "ILSVRC2012_validation_ground_truth.txt"

    if not all(
        [val_dir.is_dir(), devkit_dir.is_dir(), meta_path.exists(), truth_path.exists()]
    ):
        log.error(
            "検証データの整理に必要なディレクトリまたはファイルが見つかりません。"
        )
        return

    log.info("ImageNet検証用データの整理を開始します...")
    meta = loadmat(meta_path)
    idx_to_synset = {s[0][0][0].item(): s[0][1][0] for s in meta["synsets"]}

    with open(truth_path, "r") as f:
        ground_truth = [int(line.strip()) for line in f.readlines()]

    image_files = sorted([p for p in val_dir.glob("*.JPEG") if p.is_file()])

    if len(image_files) != 50000:
        log.warning(
            f"予期される画像数50,000に対し、{len(image_files)}個の画像が見つかりました。"
        )

    for img_path in tqdm(image_files, desc="検証用画像の整理中"):
        try:
            img_idx = int(img_path.stem.split("_")[-2])
        except (IndexError, ValueError):
            log.warning(
                f"ファイル名からインデックスを抽出できませんでした: {img_path.name}。スキップします。"
            )
            continue

        class_idx = ground_truth[img_idx - 1]
        synset_name = idx_to_synset.get(class_idx)

        if not synset_name:
            log.warning(
                f"クラスインデックス {class_idx} に対応するsynsetが見つかりません。"
            )
            continue

        dest_folder = val_dir / synset_name
        dest_folder.mkdir(exist_ok=True)
        shutil.move(str(img_path), str(dest_folder / img_path.name))
    log.info("検証用データの整理が完了しました。")


def _download_and_process_imagenet_train(train_dir: Path) -> None:
    """ImageNetの訓練データをダウンロードし、展開・整理する。

    Args:
        train_dir(Path): 訓練データの保存先ディレクトリ。
    """
    repo_id = "ILSVRC/imagenet-1k"
    train_archives = [f"data/train_images_{i}.tar.gz" for i in range(5)]
    log.info("訓練データの処理を開始します...")

    for archive_name in train_archives:
        downloaded_path = Path(
            hf_hub_download(
                repo_id=repo_id,
                revision="script",
                filename=archive_name,
                repo_type="dataset",
                local_dir=".",
                token=HF_TOKEN,
            )
        )
        log.info(f"{archive_name} からファイルを展開・整理しています...")
        with tarfile.open(downloaded_path, "r:gz") as tar:
            for member in tqdm(tar.getmembers(), desc=f"{archive_name}を処理中"):
                if not member.isfile():
                    continue
                class_id, image_id = Path(member.name).stem.split("_", 1)
                new_filename = f"{class_id}_{image_id}.JPEG"
                class_dir = train_dir / class_id
                class_dir.mkdir(exist_ok=True)
                dest_path = class_dir / new_filename
                source_file = tar.extractfile(member)
                if source_file:
                    with open(dest_path, "wb") as dest_file:
                        shutil.copyfileobj(source_file, dest_file)
        downloaded_path.unlink()
    log.info("訓練データの処理が完了しました。")


def _download_and_process_imagenet_val(val_dir: Path) -> None:
    """ImageNetの検証データをダウンロードし、展開する。

    Args:
        val_dir(Path): 検証データの保存先ディレクトリ。
    """
    repo_id = "ILSVRC/imagenet-1k"
    val_archive = "data/val_images.tar.gz"
    log.info("検証データの処理を開始します...")
    downloaded_path = Path(
        hf_hub_download(
            repo_id=repo_id,
            revision="script",
            filename=val_archive,
            repo_type="dataset",
            local_dir=".",
            token=HF_TOKEN,
        )
    )
    run_command(
        ["tar", "--no-same-owner", "-xf", str(downloaded_path), "-C", str(val_dir)]
    )
    downloaded_path.unlink()
    log.info("検証データの展開が完了しました。")


def _download_and_process_imagenet_devkit(dest_dir: Path) -> None:
    """ImageNet DevKitをダウンロードし、展開する。

    Args:
        dest_dir(Path): DevKitの保存先ディレクトリ。
    """
    devkit_url = "https://image-net.org/data/ILSVRC/2012/ILSVRC2012_devkit_t12.tar.gz"
    archive_path = dest_dir / "ILSVRC2012_devkit_t12.tar.gz"
    log.info("DevKitのダウンロードと展開を開始します...")
    try:
        with (
            urllib.request.urlopen(devkit_url) as response,
            open(archive_path, "wb") as out_file,
        ):
            shutil.copyfileobj(response, out_file)
    except urllib.error.URLError as e:
        log.error(f"DevKitのダウンロードに失敗しました: {e}")
        sys.exit(1)
    _extract_tar(archive_path, dest_dir)
    log.info("DevKitの処理が完了しました。")


@app.command()
def download_imagenet() -> None:
    """ImageNet-1kデータセット全体をダウンロードし、整理する。"""
    log.info("ImageNet-1kデータセットのダウンロードと整理を開始します...")
    dest_dir = BASE_DATASET_DIR / "ImageNet"
    train_dir = dest_dir / "train"
    val_dir = dest_dir / "val"
    train_dir.mkdir(parents=True, exist_ok=True)
    val_dir.mkdir(parents=True, exist_ok=True)

    if not HF_TOKEN:
        log.error("環境変数 HF_TOKEN が設定されていません。")
        sys.exit(1)

    _download_and_process_imagenet_train(train_dir)
    _download_and_process_imagenet_val(val_dir)
    _download_and_process_imagenet_devkit(dest_dir)
    organize_imagenet_validation_data(dest_dir)
    log.info("ImageNet-1kデータセットのダウンロードと整理が完了しました。")

    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    if DISCORD_TOKEN:
        discord_webhook = DiscordWebhook(DISCORD_TOKEN)
        discord_webhook.send(
            title="ImageNet-1K Download Completed",
            message="ImageNet-1Kデータセットのダウンロードと整理が完了しました。",
        )


if __name__ == "__main__":
    app()
