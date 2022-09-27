import extruct
import requests
from boilerpy3 import extractors
from w3lib.html import get_base_url

# Will work with website text extraction as a separate component

MAX_RECURSION_DEPTH = 10

extractor = extractors.CanolaExtractor(raise_on_failure=False)


def recursive_scan(
    o, target_keys=["content", "og:description"], skip_keys=["microformat"], depth=1
):  # noqa: B950
    if depth >= MAX_RECURSION_DEPTH:
        return []
    results = []
    if isinstance(o, dict):
        for k in o.keys():
            if k in skip_keys:
                continue
            if k in target_keys:
                # print("depth:", depth)
                results.append(o[k])
            results.extend(recursive_scan(o[k], depth=depth + 1))
    if isinstance(o, list):
        for item in o:
            results.extend(recursive_scan(item, depth=depth + 1))
    return results


def meta_from_website(html_doc, url):
    base_url = get_base_url(html_doc, url)
    meta = extruct.extract(html_doc, base_url=base_url)
    text = recursive_scan(meta)
    text = ". ".join([item for item in text if item.strip() != ""])
    return text


def boil_html(html_doc):
    from tidylib import tidy_document

    if html_doc != html_doc:
        return None
    cnt = extractor.get_content(html_doc)
    sents = cnt.split("\n")
    sents = [sent for sent in sents if len(sent.split(" ")) > 6]
    cnt = ". ".join([sent[0:-1] if sent.endswith(".") else sent for sent in sents])
    return cnt


def fetch_content(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 12.0; rv:94.0) Gecko/20100101 Firefox/94.0"
    }
    try:
        r = requests.get(url, headers=headers, timeout=3)
    except Exception as e:
        print(f"URL FAILURE: {url}")
        return None
    return r.text


def get_text_from_website(url):
    html_doc = fetch_content(url)
    if html_doc == None:
        return "", ""
    meta = meta_from_website(html_doc, url)
    boiled_content = boil_html(html_doc)
    return meta, boiled_content
