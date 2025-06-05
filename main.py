import feedparser
import requests
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime

RSS_URL = "https://feed.alternativeto.net/news/all"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
XML_FILE = "rss.xml"

def create_xml_if_not_exists():
    if not os.path.exists(XML_FILE):
        rss = ET.Element("rss", version="2.0")
        channel = ET.SubElement(rss, "channel")
        ET.SubElement(channel, "title").text = "My Summarized Feed"
        ET.SubElement(channel, "link").text = "https://your-channel-link"
        ET.SubElement(channel, "description").text = "Summarized posts using Gemini"
        tree = ET.ElementTree(rss)
        tree.write(XML_FILE, encoding="utf-8", xml_declaration=True)

def post_exists_in_xml(guid):
    if not os.path.exists(XML_FILE):
        return False
    tree = ET.parse(XML_FILE)
    root = tree.getroot()
    channel = root.find("channel")
    for item in channel.findall("item"):
        if item.find("guid").text == guid:
            return True
    return False

def add_post_to_xml(title, link, guid, pub_date, summary):
    tree = ET.parse(XML_FILE)
    root = tree.getroot()
    channel = root.find("channel")
    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "link").text = link
    ET.SubElement(item, "guid").text = guid
    ET.SubElement(item, "pubDate").text = pub_date
    ET.SubElement(item, "description").text = summary
    tree.write(XML_FILE, encoding="utf-8", xml_declaration=True)

def summarize_with_gemini(text, max_retries=10, wait_seconds=10):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"لخص النص في فقرة قصيرة بالعربية:\n{text}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    headers = {'Content-Type': 'application/json'}

    for attempt in range(max_retries):
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            try:
                return data['candidates'][0]['content']['parts'][0]['text']
            except Exception:
                return None
        else:
            if response.status_code == 503 or "overloaded" in response.text:
                print(f"محاولة {attempt+1} فشلت بسبب ازدحام الخدمة. إعادة المحاولة بعد {wait_seconds} ثانية...")
                time.sleep(wait_seconds)
            else:
                print(f"حدث خطأ آخر في الاتصال بـ Gemini: {response.text}")
                return None
    print("فشلت كل المحاولات مع Gemini.")
    return None

def main():
    create_xml_if_not_exists()
    feed = feedparser.parse(RSS_URL)
    entries = feed.entries
    if not entries:
        print("لا توجد منشورات في الخلاصة.")
        return

    # ترتيب المنشورات من الأقدم للأحدث
    entries = sorted(entries, key=lambda e: e.get('published_parsed', 0))

    for entry in entries:
        post_id = entry.get('id') or entry.get('link')
        if not post_id:
            continue

        if post_exists_in_xml(post_id):
            continue

        title = entry.get('title', 'No Title')
        link = entry.get('link', '')
        description = entry.get('summary', '')
        pub_date = entry.get('published', datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000'))

        summary = summarize_with_gemini(description)
        if summary is None:
            print("لم يتم حفظ المنشور بسبب فشل التلخيص في كل المحاولات.")
            continue

        print(f"حفظ منشور: {post_id}")
        print("الملخص:\n", summary)

        add_post_to_xml(title, link, post_id, pub_date, summary)
        print("تم الحفظ في ملف XML.")

if __name__ == "__main__":
    main()

