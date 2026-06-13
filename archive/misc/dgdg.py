import urllib.request
import urllib.parse
import re

def search(query):
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        html = urllib.request.urlopen(req).read().decode('utf-8')
        links = re.findall(r'<a class="result__snippet[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL)
        for link, snippet in links:
            print(f"{link}\n{snippet}\n")
    except Exception as e:
        print(f"Error: {e}")

search("HS/Link file transfer protocol Samuel H. Smith specification")
