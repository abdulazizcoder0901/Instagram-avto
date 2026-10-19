"""Buffer GraphQL API: posting jadvali va post yaratish."""
import os
from datetime import date as Date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import requests

API = "https://api.buffer.com"
CHANNEL_ID = os.environ.get("BUFFER_CHANNEL_ID", "6ad2a15f778b240e2f30588e")
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _gql(query, variables=None):
    r = requests.post(API, timeout=60, json={"query": query, "variables": variables or {}},
                      headers={"Authorization": f"Bearer {os.environ['BUFFER_API_KEY']}"})
    r.raise_for_status()
    body = r.json()
    if body.get("errors"):
        raise RuntimeError(f"Buffer: {body['errors'][0].get('message')}")
    return body["data"]


def slot_on(day):
    """Buffer jadvalidagi shu kunning (YYYY-MM-DD) posting vaqti. Jadvalda vaqt bo'lmasa — 10:00."""
    data = _gql("""query($id: ChannelId!) { channel(input: {id: $id}) {
        timezone postingSchedule { day times paused } } }""", {"id": CHANNEL_ID})["channel"]
    tz = ZoneInfo(data["timezone"])
    d = Date.fromisoformat(day)
    for entry in data["postingSchedule"]:
        if entry["day"] == DAYS[d.weekday()] and not entry["paused"] and entry["times"]:
            hh, mm = map(int, sorted(entry["times"])[0].split(":"))
            return datetime.combine(d, time(hh, mm), tz)
    return datetime.combine(d, time(10, 0), tz)


def create_post(image_urls, caption, alt_text, due_at=None):
    """Carousel postni avtomatik chiqishga qo'yadi. due_at bo'lmasa darhol chiqaradi.
    Musiqa qo'shilmaydi: Instagram API orqali chiqqan carousel'ga musiqani qabul qilmaydi."""
    instagram = {"type": "post", "shouldShareToFeed": True, "isAiGenerated": True}
    variables = {"input": {
        "channelId": CHANNEL_ID,
        "text": caption,
        "schedulingType": "automatic",
        "mode": "customScheduled" if due_at else "shareNow",
        "assets": [{"image": {"url": u, "metadata": {"altText": alt_text}}} for u in image_urls],
        "metadata": {"instagram": instagram},
        "aiAssisted": True,
    }}
    if due_at:
        variables["input"]["dueAt"] = due_at.isoformat()
    data = _gql("""mutation($input: CreatePostInput!) { createPost(input: $input) {
        __typename
        ... on PostActionSuccess { post { id status dueAt } }
        ... on MutationError { message } } }""", variables)["createPost"]
    if data["__typename"] != "PostActionSuccess":
        raise RuntimeError(f"Buffer post yaratmadi: {data.get('message')}")
    return data["post"]


def publish_time(now, day):
    """Post sanasidagi vaqt; u o'tib ketgan bo'lsa None (darhol chiqarish)."""
    slot = slot_on(day)
    return slot if slot > now + timedelta(minutes=3) else None


def post_status(post_id):
    """(holat, chiqish vaqti): holat — scheduled, sending, sent, error..."""
    post = _gql("""query($id: PostId!) { post(input: {id: $id}) { status dueAt } }""", {"id": post_id})["post"]
    return post["status"], post["dueAt"]


def post_result(post_id):
    """Chiqqan postning holati, Instagram linki va xato matni."""
    post = _gql("""query($id: PostId!) { post(input: {id: $id}) { status externalLink error { message } } }""",
                {"id": post_id})["post"]
    return post["status"], post.get("externalLink"), (post.get("error") or {}).get("message")


def delete_post(post_id):
    data = _gql("""mutation($id: PostId!) { deletePost(input: {id: $id}) {
        __typename ... on MutationError { message } } }""", {"id": post_id})["deletePost"]
    if data["__typename"] != "DeletePostSuccess":
        raise RuntimeError(f"Buffer postni o'chirmadi: {data.get('message')}")


if __name__ == "__main__":
    print(slot_on(datetime.now(ZoneInfo("Asia/Tashkent")).strftime("%Y-%m-%d")))
