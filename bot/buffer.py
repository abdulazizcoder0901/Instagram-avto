"""Buffer GraphQL API: posting jadvali, Instagram musiqa katalogi va post yaratish."""
import os
from datetime import datetime, timedelta
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


def todays_slot(now):
    """Buffer'dagi bugungi posting vaqti (kanal vaqt zonasida) yoki None."""
    data = _gql("""query($id: ChannelId!) { channel(input: {id: $id}) {
        timezone postingSchedule { day times paused } } }""", {"id": CHANNEL_ID})["channel"]
    tz = ZoneInfo(data["timezone"])
    local = now.astimezone(tz)
    day = DAYS[local.weekday()]
    for entry in data["postingSchedule"]:
        if entry["day"] == day and not entry["paused"] and entry["times"]:
            hh, mm = map(int, sorted(entry["times"])[0].split(":"))
            return local.replace(hour=hh, minute=mm, second=0, microsecond=0)
    return None


def music_options(query, limit=5):
    """Instagram musiqa katalogidan variantlar. Kanal Facebook Login orqali ulanmagan bo'lsa None."""
    q = """query($ch: ChannelId!, $q: String!) {
      search: searchInstagramAudio(input: {channelId: $ch, audioType: music, query: $q}) {
        __typename ... on SearchInstagramAudioSuccess { audio { id title displayArtist } } }
      trending: trendingInstagramAudio(input: {channelId: $ch, audioType: music}) {
        __typename ... on SearchInstagramAudioSuccess { audio { id title displayArtist } } } }"""
    data = _gql(q, {"ch": CHANNEL_ID, "q": query})
    if data["search"]["__typename"] != "SearchInstagramAudioSuccess":
        return None
    found = data["search"].get("audio", [])
    trending = (data.get("trending") or {}).get("audio", [])
    # qidiruvdan 3 ta + trenddan 2 ta, yetmasa qolganidan to'ldiriladi
    candidates = found[:3] + trending[:2] + found[3:] + trending[2:]
    seen, out = set(), []
    for a in candidates:
        if a["id"] not in seen and len(out) < limit:
            seen.add(a["id"])
            out.append({"id": a["id"], "title": a["title"], "artist": a.get("displayArtist") or ""})
    return out


def create_post(image_urls, caption, alt_text, due_at=None, music=None, reminder=False):
    """Carousel post yaratadi. due_at bo'lmasa darhol chiqaradi."""
    instagram = {"type": "post", "shouldShareToFeed": True, "isAiGenerated": True}
    if music:
        instagram["stickerFields"] = {"music": music}
    variables = {"input": {
        "channelId": CHANNEL_ID,
        "text": caption,
        "schedulingType": "notification" if reminder else "automatic",
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


def publish_time(now):
    """Bugungi slot hali o'tmagan bo'lsa o'sha vaqt, aks holda None (darhol chiqarish)."""
    slot = todays_slot(now)
    if slot and slot > now + timedelta(minutes=3):
        return slot
    return None


if __name__ == "__main__":
    print(todays_slot(datetime.now(ZoneInfo("Asia/Tashkent"))))
