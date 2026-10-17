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


AUDIO_FIELDS = "__typename ... on SearchInstagramAudioSuccess { audio { id title displayArtist previewUrl } }"


def music_catalog(suggestions, limit=5):
    """Instagram musiqa katalogidan treklar (namunasi bilan). Kanal Facebook Login orqali ulanmagan bo'lsa None."""
    def search(q):
        data = _gql(f"""query($ch: ChannelId!, $q: String!) {{
            r: searchInstagramAudio(input: {{channelId: $ch, audioType: music, query: $q}}) {{ {AUDIO_FIELDS} }} }}""",
                    {"ch": CHANNEL_ID, "q": q})["r"]
        return data.get("audio") if data["__typename"] == "SearchInstagramAudioSuccess" else None

    out, seen = [], set()
    for s in suggestions:
        found = search(f"{s['title']} {s['artist']}")
        if found is None:
            return None
        for a in found[:1]:
            if a["id"] not in seen:
                seen.add(a["id"])
                out.append(a)
    if len(out) < limit:
        trending = _gql(f"""query($ch: ChannelId!) {{
            r: trendingInstagramAudio(input: {{channelId: $ch, audioType: music}}) {{ {AUDIO_FIELDS} }} }}""",
                        {"ch": CHANNEL_ID})["r"]
        out += [a for a in trending.get("audio", []) if a["id"] not in seen][:limit - len(out)]
    return [{"id": a["id"], "title": a["title"], "artist": a.get("displayArtist") or "",
             "preview_url": a.get("previewUrl")} for a in out[:limit]]


def create_post(image_urls, caption, alt_text, due_at=None, music=None):
    """Carousel postni avtomatik chiqishga qo'yadi. due_at bo'lmasa darhol chiqaradi; music — katalog trek id."""
    instagram = {"type": "post", "shouldShareToFeed": True, "isAiGenerated": True}
    if music:
        instagram["stickerFields"] = {"music": music}
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


def publish_time(now):
    """Bugungi slot hali o'tmagan bo'lsa o'sha vaqt, aks holda None (darhol chiqarish)."""
    slot = todays_slot(now)
    if slot and slot > now + timedelta(minutes=3):
        return slot
    return None


if __name__ == "__main__":
    print(todays_slot(datetime.now(ZoneInfo("Asia/Tashkent"))))
