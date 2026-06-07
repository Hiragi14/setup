import json
import socket
from datetime import datetime
from logging import getLogger

import requests
import typer

app = typer.Typer()
log = getLogger(__name__)


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


@app.command()
def notice(
    title: str = typer.Option(..., "-t", "--title", help="通知のタイトル"),
    message: str = typer.Option("", "-m", "--message", help="通知の内容"),
    webhook_url: str = typer.Option(
        ..., "-w", "--webhook-url", help="DiscordのWebhook URL"
    ),
    footer: bool = typer.Option(True, help="フッターを表示するかどうか"),
):
    """Discordに通知を送信するコマンド

    Args:
        title (str): 通知のタイトル
        message (str): 通知の内容
        webhook_url (str): DiscordのWebhook URL
        footer (bool): フッターを表示するかどうか
    """
    discord_webhook = DiscordWebhook(webhook_url)
    discord_webhook.send(title, message, footer)


if __name__ == "__main__":
    app()
