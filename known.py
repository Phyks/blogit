#!/usr/bin/env python3
from bs4 import BeautifulSoup
from bs4.element import Comment
import os
import base64
import hashlib
import hmac
import requests
import sys

"""
Script to import articles from a blogit blog in Known.

Must be run with a correct API_KEY (see below) and from the `gen/` folder.
"""


def list_directory(path):
    fichier = []
    for root, dirs, files in os.walk(path):
        for i in files:
            fichier.append(os.path.join(root, i))
    return fichier


def hmac_sha256(message, key):
    return base64.b64encode(hmac.new(key.encode("utf-8"),
                                     message.encode("utf-8"),
                                     digestmod=hashlib.sha256)
                            .digest()).decode("utf-8")


def known_api(username, api_key, type, payload):
    headers = {
        "X-KNOWN-USERNAME": username,
        "X-KNOWN-SIGNATURE": hmac_sha256("/"+type+"/edit", api_key)
    }
    return requests.post("https://known.phyks.me/"+type+"/edit",
                         data=payload,
                         headers=headers)

if len(sys.argv) < 3:
    print("Usage: "+sys.argv[0]+" USERNAME API_KEY [file]")
    sys.exit()

API_USERNAME = sys.argv[1]
API_KEY = sys.argv[2]
if len(sys.argv) <= 3:
    files = [list_directory(i) for i in ["2013", "2014", "2015"]]
else:
    files = [sys.argv[3]]

for file in files:
    print("Processing file "+file)
    with open(file, 'r') as fh:
        soup = BeautifulSoup(fh.read())

    content = []
    for i in soup.div.find('header').next_siblings:
        if i.name == "footer":
            break
        if type(i) != Comment:
            content.append(i)
    comment = soup.div.findAll(text=lambda text: isinstance(text,
                                                            Comment))
    comment = [i.strip() for i in comment[0].strip().split('\n')]
    for j in comment:
        if j.startswith("@title"):
            title = j.split("=")[1]
        elif j.startswith("@date"):
            date = j.split("=")[1]
        elif j.startswith("@tags"):
            tags = j.split("=")[1]
            tags = ', '.join(["#"+i.strip() for i in tags.split(',')])
    meta = {
        "title": title,
        "date": (str(date[4:8])+":"+str(date[2:4])+":"+str(date[0:2]) +
                 " "+str(date[9:11])+":"+str(date[11:13])+":00"),
        "tags": tags,
    }

    content = ''.join([str(i) for i in content]).strip()
    content += "\n<p>"+meta["tags"]+"</p>"
    payload = {"body": content,
               "title": meta["title"],
               "created": meta["date"]}
    known_api(API_USERNAME, API_KEY, "entry", payload)
