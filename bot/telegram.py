"""Telegram Bot API uchun minimal mijoz."""
import json
import os

import requests


class Telegram:
    def __init__(self):
        self.base = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}"
        self.chat_id = int(os.environ["TELEGRAM_CHAT_ID"])
        self.offset = None

    def _call(self, method, timeout=60, files=None, **params):
        if files:
            data = {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in params.items()}
            r = requests.post(f"{self.base}/{method}", data=data, files=files, timeout=timeout)
        else:
            r = requests.post(f"{self.base}/{method}", json=params, timeout=timeout)
        body = r.json()
        if not body.get("ok"):
            raise RuntimeError(f"Telegram {method}: {body.get('description')}")
        return body["result"]

    def send(self, text, buttons=None):
        params = {"chat_id": self.chat_id, "text": text, "disable_web_page_preview": True}
        if buttons:
            params["reply_markup"] = {"inline_keyboard": [
                [{"text": label, "callback_data": data} for label, data in row] for row in buttons
            ]}
        return self._call("sendMessage", **params)

    def send_album(self, paths):
        files = {f"p{i}": open(p, "rb") for i, p in enumerate(paths)}
        try:
            media = [{"type": "photo", "media": f"attach://p{i}"} for i in range(len(paths))]
            return self._call("sendMediaGroup", timeout=180, files=files,
                              chat_id=self.chat_id, media=media)
        finally:
            for f in files.values():
                f.close()

    def clear_buttons(self, message_id):
        try:
            self._call("editMessageReplyMarkup", chat_id=self.chat_id, message_id=message_id,
                       reply_markup={"inline_keyboard": []})
        except RuntimeError:
            pass

    def answer(self, callback_id, text=""):
        self._call("answerCallbackQuery", callback_query_id=callback_id, text=text)

    def skip_pending(self):
        """Bot ishga tushishidan oldingi eski xabarlarni o'tkazib yuboradi."""
        updates = self._call("getUpdates", offset=-1, timeout=0)
        if updates:
            self.offset = updates[-1]["update_id"] + 1

    def events(self, poll_seconds=50):
        """Faqat egasining chatidan kelgan ('button', data, cb_id, msg_id) yoki ('text', matn) hodisalari."""
        params = {"timeout": poll_seconds, "allowed_updates": ["message", "callback_query"]}
        if self.offset is not None:
            params["offset"] = self.offset
        try:
            updates = self._call("getUpdates", timeout=poll_seconds + 15, **params)
        except requests.RequestException:
            return []
        out = []
        for u in updates:
            self.offset = u["update_id"] + 1
            if "callback_query" in u:
                cb = u["callback_query"]
                if cb["message"]["chat"]["id"] == self.chat_id:
                    out.append(("button", cb["data"], cb["id"], cb["message"]["message_id"]))
            elif "message" in u and u["message"]["chat"]["id"] == self.chat_id:
                text = u["message"].get("text", "").strip()
                if text:
                    out.append(("text", text))
        return out
