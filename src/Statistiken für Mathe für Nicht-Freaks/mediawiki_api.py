from sys import stderr
import urllib.request
import requests
import datetime
import os
import json
import time


def get_section_id(request_session, topic):
    # in try-catch
    PARAMS = {
        "action": "parse",
        "page": "Mathe_für_Nicht-Freaks:_Sitemap",
        "prop": "sections",
        "format": "json"
    }

    R = request_session.get(url="https://de.wikibooks.org/w/api.php", params=PARAMS)
    data = R.json()

    for section in data["parse"]["sections"]:
        if section["line"] == topic:
            return section["index"]


def scrape_sitemap_topic(request_session, section_id):
    PARAMS = {
        "action": "parse",
        "page": "Mathe_für_Nicht-Freaks:_Sitemap",
        "section": str(section_id),
        "prop": "links",
        "format": "json"
    }

    R = request_session.get(url="https://de.wikibooks.org/w/api.php", params=PARAMS)
    data = R.json()
    return [link["*"] for link in data["parse"]["links"] if link["ns"] == 0 and "exists" in link.keys()]


def scrape_sitemap(request_session, *topics):
    section_ids = {topic: get_section_id(request_session, topic) for topic in topics}
    topic_links = {}
    for topic, id in section_ids.items():
        topic_links[topic] = scrape_sitemap_topic(request_session, id)
    return topic_links


def save_whole_sitemap(topic_links):
    os.makedirs("sitemap", exist_ok=True)
    for topic, links in topic_links.items():
        with open("sitemap/" + topic.replace(" ", "_") + ".txt", "w+") as file:
            for link in links:
                file.write("%s\n" % link)


def get_article_revisions(title, request_session, retries=3, delay=10, **kwargs):
    for i in range(retries):
        result = _get_article_revisions(title, request_session, **kwargs)
        if result is not None:
            return result
        time.sleep(delay)  # Wartezeit zwischen den Wiederholungen
    return []


def _get_article_revisions(title, request_session, options=None, start_date=None, end_date=None):
    if options is None:
        options = dict()
    if end_date is None:
        end_date = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    if start_date is None:
        PARAMS = {
            "action": "query",
            "prop": "revisions",
            "titles": title,
            "rvlimit": "max",
            "rvprop": "timestamp|user",
            "rvdir": "newer",
            "rvend": str(end_date),
            "rvslots": "main",
            "formatversion": "2",
            "format": "json",
            **options
        }
    else:
        PARAMS = {
            "action": "query",
            "prop": "revisions",
            "titles": title,
            "rvlimit": "max",
            "rvprop": "timestamp|user",
            "rvdir": "newer",
            "rvstart": str(start_date),
            "rvend": str(end_date),
            "rvslots": "main",
            "formatversion": "2",
            "format": "json",
            **options
        }

    try:
        R = request_session.get(url="https://de.wikibooks.org/w/api.php", params=PARAMS)
        data = R.json()
    except requests.exceptions.RequestException as e:
        print(f"\033[91m Netzwerkfehler bei Artikel {title}: {e} \033[0m", file=stderr)
        return []
    except json.JSONDecodeError:
        print(f"\033[91m Fehler beim Parsen der Antwort für Artikel {title} \033[0m", file=stderr)
        return []

    if "error" in data.keys():
        print(f"\033[91m API-Fehler bei Artikel {title}: {data['error']} \033[0m", file=stderr)
        return []

    if "continue" in data.keys():
        options["rvcontinue"] = data["continue"]["rvcontinue"]
        return data["query"]["pages"][0]["revisions"] + _get_article_revisions(title, request_session, options)
    else:
        if "query" in data and "pages" in data["query"] and len(data["query"]["pages"]) > 0:
            if "revisions" in data["query"]["pages"][0]:
                print("\033[92m History successfully generated for article %s \033[0m" % title, file=stderr)
                return data["query"]["pages"][0]["revisions"]
            else:
                print("\033[94m History successfully generated for article %s - no new edits\033[0m" % title, file=stderr)
                return []


def build_revision_db(request_session, *topics):
    os.makedirs("revisions", exist_ok=True)
    topic_links = scrape_sitemap(request_session, *topics)
    for topic, links in topic_links.items():
        with open("revisions/" + topic.replace(" ", "_") + ".txt", "w+") as file:
            for link in links:
                json.dump(_get_article_revisions(link, request_session), file)
                file.write("\n")


if __name__ == "__main__":
    S = requests.Session()
    print(_get_article_revisions("Mathe_für_Nicht-Freaks:_Sitemap", S, end_date="2020-05-14"), file=stderr)
