#!/usr/bin/env python3

# Blogit script written by Phyks (Lucas Verney) for his personnal use. I
# distribute it with absolutely no warranty, except that it works for me on my
# blog :)

# This script is a pre-commit hook that should be placed in your .git/hooks
# folder to work. Read README file for more info.

# LICENSE :
# -----------------------------------------------------------------------------
# "THE NO-ALCOHOL BEER-WARE LICENSE" (Revision 42):
# Phyks (webmaster@phyks.me) wrote this file. As long as you retain this notice
# you can do whatever you want with this stuff (and you can also do whatever
# you want with this stuff without retaining it, but that's not cool...). If
# we meet some day, and you think this stuff is worth it, you can buy me a
# <del>beer</del> soda in return.
#									Phyks
#  ----------------------------------------------------------------------------

import sys
import getopt
import shutil
import os
import datetime
import subprocess
import re
import locale
import markdown
from email import utils
from hashlib import md5

from functools import cmp_to_key
from time import gmtime, strftime, mktime
from bs4 import BeautifulSoup


# ========================
# Github Flavored Markdown
# ========================

def gfm(text):
    # Extract pre blocks.
    extractions = {}

    def pre_extraction_callback(matchobj):
        digest = md5(matchobj.group(0)).hexdigest()
        extractions[digest] = matchobj.group(0)
        return "{gfm-extraction-%s}" % digest
    pattern = re.compile(r'<pre>.*?</pre>', re.MULTILINE | re.DOTALL)
    text = re.sub(pattern, pre_extraction_callback, text)

    # Prevent foo_bar_baz from ending up with an italic word in the middle.
    def italic_callback(matchobj):
        s = matchobj.group(0)
        if list(s).count('_') >= 2:
            return s.replace('_', '\_')
        return s
    text = re.sub(r'^(?! {4}|\t)\w+_\w+_\w[\w_]*', italic_callback, text)

    # In very clear cases, let newlines become <br /> tags.
    def newline_callback(matchobj):
        if len(matchobj.group(1)) == 1:
            return matchobj.group(0).rstrip() + ' \n'
        else:
            return matchobj.group(0)
    pattern = re.compile(r'^[\w\<][^\n]*(\n+)', re.MULTILINE)
    text = re.sub(pattern, newline_callback, text)

    # Insert pre block extractions.
    def pre_insert_callback(matchobj):
        return '\n\n' + extractions[matchobj.group(1)]
    text = re.sub(r'{gfm-extraction-([0-9a-f]{32})\}', pre_insert_callback,
                  text)

    return text


# Test suite.
try:
    from nose.tools import assert_equal
except ImportError:
    def assert_equal(a, b):
        assert a == b, '%r != %r' % (a, b)


def test_single_underscores():
    """Don't touch single underscores inside words."""
    assert_equal(
        gfm('foo_bar'),
        'foo_bar',
    )


def test_underscores_code_blocks():
    """Don't touch underscores in code blocks."""
    assert_equal(
        gfm(' foo_bar_baz'),
        ' foo_bar_baz',
    )


def test_underscores_pre_blocks():
    """Don't touch underscores in pre blocks."""
    assert_equal(
        gfm('<pre>\nfoo_bar_baz\n</pre>'),
        '\n\n<pre>\nfoo_bar_baz\n</pre>',
    )


def test_pre_block_pre_text():
    """Don't treat pre blocks with pre-text differently."""
    a = '\n\n<pre>\nthis is `a\\_test` and this\\_too\n</pre>'
    b = 'hmm<pre>\nthis is `a\\_test` and this\\_too\n</pre>'
    assert_equal(
        gfm(a)[2:],
        gfm(b)[3:],
    )


def test_two_underscores():
    """Escape two or more underscores inside words."""
    assert_equal(
        gfm('foo_bar_baz'),
        'foo\\_bar\\_baz',
    )


def test_newlines_simple():
    """Turn newlines into br tags in simple cases."""
    assert_equal(
        gfm('foo\nbar'),
        'foo \nbar',
    )


def test_newlines_group():
    """Convert newlines in all groups."""
    assert_equal(
        gfm('apple\npear\norange\n\nruby\npython\nerlang'),
        'apple \npear \norange\n\nruby \npython \nerlang',
    )


def test_newlines_long_group():
    """Convert newlines in even long groups."""
    assert_equal(
        gfm('apple\npear\norange\nbanana\n\nruby\npython\nerlang'),
        'apple \npear \norange \nbanana\n\nruby \npython \nerlang',
    )


def test_newlines_list():
    """Don't convert newlines in lists."""
    assert_equal(
        gfm('# foo\n# bar'),
        '# foo\n# bar',
    )
    assert_equal(
        gfm('* foo\n* bar'),
        '* foo\n* bar',
    )

# =========
# Functions
# =========


# Test if a variable exists (== isset function in PHP)
# ====================================================
def isset(variable):
    return variable in locals() or variable in globals()


# Test wether a variable is an int or not
# =======================================
def isint(variable):
    try:
        int(variable)
        return True
    except ValueError:
        return False


# List all files in path directory
# Works recursively
# Return files list with path relative to current dir
# ===================================================
def list_directory(path):
    fichier = []
    for root, dirs, files in os.walk(path):
        for i in files:
            fichier.append(os.path.join(root, i))
    return fichier


# Return a list with the tags of a given article
# ==============================================
def get_tags(filename):
    try:
        with open(filename, 'r') as fh:
            tag_line = ''
            for line in fh.readlines():
                if "@tags=" in line:
                    tag_line = line
                    break

            if not tag_line:
                return []

            tags = [x.strip() for x in line[line.find("@tags=")+6:].split(",")]
            return tags
    except IOError:
        sys.exit("[ERROR] Unable to open file "+filename+".")


#Return date of an article
# ========================
def get_date(filename):
    try:
        with open(filename, 'r') as fh:
            for line in fh.readlines():
                if "@date=" in line:
                    return line[line.find("@date=")+6:].strip()
        sys.exit("[ERROR] Unable to determine date in article "+filename+".")
    except IOError:
        sys.exit("[ERROR] Unable to open file "+filename+".")


# Return the _number_ latest articles in _dir_ directory
# ======================================================
def latest_articles(directory, number):
    try:
        latest_articles = subprocess.check_output(["git",
                                                   "ls-files",
                                                   directory],
                                                  universal_newlines=True)
    except:
        sys.exit("[ERROR] An error occurred when fetching file changes "
                 "from git.")
    latest_articles = latest_articles.strip().split("\n")
    latest_articles = [x for x in latest_articles if(isint(x[4:8]) and
                                                     (x.endswith(".html") or
                                                      x.endswith(".md")))]
    latest_articles.sort(key=lambda x: (get_date(x)[4:8], get_date(x)[2:4],
                                        get_date(x)[:2], get_date(x)[9:]),
                         reverse=True)
    return latest_articles[:number]


# Auto create necessary directories to write a file
# =================================================
def auto_dir(path):
    directory = os.path.dirname(path)
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except IOError:
        sys.exit("[ERROR] An error occurred while creating "+path+" file "
                 "and parent dirs.")


# Replace some user specific syntax tags (to repplace smileys for example)
# ========================================================================
def replace_tags(article, search_list, replace_list):
    return_string = article
    for search, replace in zip(search_list, replace_list):
        return_string = re.sub(search, replace, article)
    return return_string


# Return text in <div class="article"> for rss description
# ========================================================
def get_text_rss(content):
    soup = BeautifulSoup(content)
    date = soup.find(attrs={'class': 'date'})
    date.extract()
    title = soup.find(attrs={'class': 'article_title'})
    title.extract()
    return str(soup.div)


def remove_tags(html):
    return ''.join(BeautifulSoup(html).findAll(text=True))


def truncate(text, length=100):
    return text[:text.find('.', length) - 1] + "…"

# Set locale
locale.setlocale(locale.LC_ALL, '')


# ========================
# Start of the main script
# ========================
try:
    opts, args = getopt.gnu_getopt(sys.argv, "hf", ["help", "force-regen"])
except getopt.GetoptError:
    sys.exit("[ERROR] Unable to parse command line arguments. "
             "See pre-commit -h for more infos on how to use.")

force_regen = False
for opt, arg in opts:
    if opt in ("-h", "--help"):
        print("Usage :")
        print("This should be called automatically as a pre-commit git hook. "
              "You can also launch it manually right before commiting.\n")
        print("This script generates static pages ready to be served behind "
              "your webserver.\n")
        print("Usage :")
        print("-h \t --help \t displays this help message.")
        print("-f \t --force-regen \t force complete rebuild of all pages.")
        sys.exit(0)
    elif opt in ("-f", "--force-regen"):
        force_regen = True


# Set parameters with params file
search_list = []
replace_list = []
months = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet",
          "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
try:
    with open("raw/params", "r") as params_fh:
        params = {}
        for line in params_fh.readlines():
            if line.strip() == "" or line.strip().startswith("#"):
                continue
            option, value = line.split("=", 1)
            option = option.strip()

            if option == "SEARCH":
                search_list = [i.strip() for i in value.split(",")]
            elif option == "REPLACE":
                replace_list = [i.strip() for i in value.split(",")]
            elif option == "MONTHS":
                months = [i.strip() for i in value.split(",")]
            elif option == "IGNORE_FILES":
                params["IGNORE_FILES"] = [i.strip() for i in value.split(",")]
            elif option == "BLOG_URL":
                params["BLOG_URL"] = value.strip(" \n\t\r").rstrip("/")
            else:
                params[option.strip()] = value.strip()

    print("[INFO] Parameters set from raw/params file.")
except IOError:
    sys.exit("[ERROR] Unable to load raw/params file which defines important "
             "parameters. Does such a file exist ? See doc for more info "
             "on this file.")

print("[INFO] Blog url is "+params["BLOG_URL"]+".")

# Fill lists for modified, deleted and added files
modified_files = []
deleted_files = []
added_files = []

#Lists of years and months with modified files
years_list = []
months_list = []

if not force_regen:
    # Find the changes to be committed
    try:
        changes = subprocess.check_output(["git",
                                           "diff",
                                           "--cached",
                                           "--name-status"],
                                          universal_newlines=True)
    except:
        sys.exit("[ERROR] An error occurred when fetching file changes "
                 "from git.")

    changes = changes.strip().split("\n")
    if changes == [""]:
        sys.exit("[ERROR] Nothing to do... Did you add new files with "
                 "\"git add\" before ?")

    for changed_file in changes:
        if changed_file[0].startswith("A"):
            added_files.append(changed_file[changed_file.index("\t")+1:])
        elif changed_file[0].startswith("M"):
            modified_files.append(changed_file[changed_file.index("\t")+1:])
        elif changed_file[0].startswith("D"):
            deleted_files.append(changed_file[changed_file.index("\t")+1:])
        else:
            sys.exit("[ERROR] An error occurred when running git diff.")
else:
    try:
        shutil.rmtree("blog/")
    except FileNotFoundError:
        pass
    try:
        shutil.rmtree("gen/")
    except FileNotFoundError:
        pass
    added_files = list_directory("raw")

if not added_files and not modified_files and not deleted_files:
    sys.exit("[ERROR] Nothing to do... Did you add new files with "
             "\"git add\" before ?")

# Only keep modified raw articles files
for filename in list(added_files):
    direct_copy = False

    if (not filename.startswith("raw/") or filename.endswith("~") or
       filename in params["IGNORE_FILES"]):
        added_files.remove(filename)
        continue

    try:
        int(filename[4:8])
        if filename[4:8] not in years_list:
            years_list.append(filename[4:8])
    except ValueError:
        direct_copy = True

    try:
        int(filename[9:11])
        if filename[9:11] not in months_list:
            months_list.append(filename[9:11])
    except ValueError:
        pass

    if ((not filename.endswith(".html") and not filename.endswith(".ignore")
        and not filename.endswith(".md"))
       or direct_copy):
        # Note : this deal with CSS, images or footer file
        print("[INFO] (Direct copy) Copying directly the file "
              + filename[4:]+" to blog dir.")

        auto_dir("blog/"+filename[4:])
        shutil.copy(filename, "blog/"+filename[4:])
        added_files.remove(filename)
        continue

    if filename.endswith(".ignore"):
        print("[INFO] (Not published) Found not published article "
              + filename[4:-7]+".")
        added_files.remove(filename)
        continue

for filename in list(modified_files):
    direct_copy = False

    if (not filename.startswith("raw/") or filename.endswith("~")
       or filename in params["IGNORE_FILES"]):
        modified_files.remove(filename)
        continue
    try:
        int(filename[4:8])
        if filename[4:8] not in years_list:
            years_list.append(filename[4:8])
    except ValueError:
        direct_copy = True

    try:
        int(filename[9:11])
        if filename[9:11] not in months_list:
            months_list.append(filename[9:11])
    except ValueError:
        pass

    if ((not filename.endswith(".html") and not filename.endswith(".ignore")
        and not filename.endswith(".md"))
       or direct_copy):
        print("[INFO] (Direct copy) Updating directly the file "
              + filename[4:]+" in blog dir.")
        auto_dir("blog/"+filename[4:])
        shutil.copy(filename, "blog/"+filename[4:])
        modified_files.remove(filename)
        continue

    if filename.endswith(".ignore"):
        print("[INFO] (Not published) Found not published article "
              + filename[4:-7]+".")
        added_files.remove(filename)
        continue

for filename in list(deleted_files):
    direct_copy = False

    if (not filename.startswith("raw/") or filename.endswith("~") or
       filename in params["IGNORE_FILES"]):
        deleted_files.remove(filename)
        continue

    try:
        int(filename[4:8])
        if filename[4:8] not in years_list:
            years_list.append(filename[4:8])
    except ValueError:
        direct_delete = True

    try:
        int(filename[9:11])
        if filename[9:11] not in months_list:
            months_list.append(filename[9:11])
    except ValueError:
        pass

    if ((not filename.endswith(".html") and not filename.endswith(".ignore")
        and not filename.endswith(".md"))
       or (isset("direct_delete") and direct_delete is True)):
        print("[INFO] (Deleted file) Delete directly copied file "
              + filename[4:]+" in blog dir.")
        try:
            os.unlink(filename)
        except FileNotFoundError:
            pass
        os.system('git rm '+filename)
        deleted_files.remove(filename)
        continue

print("[INFO] Added files : "+", ".join(added_files))
print("[INFO] Modified files : "+", ".join(modified_files))
print("[INFO] Deleted filed : "+", ".join(deleted_files))

print("[INFO] Updating tags for added and modified files.")
for filename in added_files:
    tags = get_tags(filename)

    if not tags:
        sys.exit("[ERROR] (TAGS) In added article "+filename[4:]+" : "
                 "No tags found !")
    for tag in tags:
        try:
            auto_dir("gen/tags/"+tag+".tmp")
            with open("gen/tags/"+tag+".tmp", 'a+') as tag_file:
                tag_file.seek(0)
                if filename[4:] not in tag_file.read():
                    tag_file.write(filename[4:]+"\n")
                print("[INFO] (TAGS) Found tag "+tag+" in article "
                      + filename[4:])
        except IOError:
            sys.exit("[ERROR] (TAGS) New tag found but an error "
                     "occurred in article "+filename[4:]+": "+tag+".")

for filename in modified_files:
    try:
        tags = get_tags(filename)
    except IOError:
        sys.exit("[ERROR] Unable to open file "+filename[4:]+".")

    if not tags:
        sys.exit("[ERROR] (TAGS) In modified article "+filename[4:]+" : "
                 " No tags found !")

    for tag in list_directory("gen/tags/"):
        try:
            with open(tag, 'r+') as tag_file:
                if (tag[tag.index("tags/") + 5:tag.index(".tmp")] in tags
                   and filename[4:] not in tag_file.read()):
                    tag_file.seek(0, 2)  # Append to end of file
                    tag_file.write(filename[4:]+"\n")
                    print("[INFO] (TAGS) Found new tag "
                          + tag[:tag.index(".tmp")]+" for modified article "
                          + filename[4:]+".")
                    tags.remove(tag_file[9:])
                if (tag[tag.index("tags/") + 5:tag.index(".tmp")] not in tags
                   and filename[4:] in tag_file.read()):
                    tag_old = tag_file.read()
                    tag_file.truncate()
                    # Delete file in tag
                    tag_file_write = tag_old.replace(filename[4:]+"\n", "")

                    if tag_file_write:
                        tag_file.write(tag_file_write)
                        print("[INFO] (TAGS) Deleted tag " +
                              tag[:tag.index(".tmp")]+" in modified article " +
                              filename[4:]+".")
                    else:
                        try:
                            os.unlink(tag)
                            print("[INFO] (TAGS) No more article with tag " +
                                  tag[8:-4]+", deleting it.")
                        except FileNotFoundError:
                            print("[INFO] (TAGS) "+tag+" was found to be empty"
                                  " but there was an error during deletion. "
                                  "You should check manually.")
                        os.system('git rm '+tag)

                    print(tags)
                    tags.remove(tag[9:])

        except IOError:
            sys.exit("[ERROR] (TAGS) An error occurred when parsing tags "
                     " of article "+filename[4:]+".")

    # New tags created
    for tag in [x for x in tags if "gen/tags/"+x+".tmp"
                not in list_directory("gen/tags")]:
        try:
            auto_dir("gen/tags/"+tag+".tmp")
            with open("gen/tags/"+tag+".tmp", "a+") as tag_file:
                tag_file.write(filename[4:]+"\n")
                print("[INFO] (TAGS) Found new tag "+tag+" for "
                      "modified article "+filename[4:]+".")
        except IOError:
            sys.exit("[ERROR] (TAGS) An error occurred when parsing tags "
                     "of article "+filename[4:]+".")

# Delete tags for deleted files and delete all generated files
for filename in deleted_files:
    tags = os.listdir("gen/tags/")

    if not tags:
        sys.exit("[ERROR] In deleted article "+filename[4:]+" : "
                 "No tags found !")

    for tag in tags:
        try:
            with open("gen/tags/"+tag, 'r+') as tag_file:
                tag_old = tag_file.read()
                tag_file.truncate()
                # Delete file in tag
                tag_file_write = tag_old.replace(filename[4:]+"\n", "")
                if tag_file_write:
                    tag_file.write(tag_file_write)
                    print("[INFO] (TAGS) Deleted tag " +
                          tag[:tag.index(".tmp")]+" in deleted article " +
                          filename[4:]+".")

        except IOError:
            sys.exit("[ERROR] An error occurred while deleting article " +
                     filename[4:]+" from tags files.")

        if not tag_file_write:
            try:
                os.unlink(tag)
                print("[INFO] (TAGS) No more article with tag " +
                      tag[8:-4]+", deleting it.")
            except FileNotFoundError:
                print("[INFO] (TAGS) "+tag+" was found to be empty "
                      "but there was an error during deletion. "
                      "You should check manually.")
            os.system('git rm '+filename)

    # Delete generated files
    try:
        os.unlink("gen/"+filename[4:-5]+".gen")
        os.unlink("blog/"+filename[4:])
    except FileNotFoundError:
        print("[INFO] (DELETION) Article "+filename[4:]+" seems "
              "to not have already been generated. "
              "You should check manually.")
    os.system("git rm gen/"+filename[4:-5]+".gen")
    os.system("git rm blog/"+filename[4:])

    print("[INFO] (DELETION) Deleted article "+filename[4:] +
          " in both gen and blog directories")


# Common lists that are used multiple times
last_articles = latest_articles("raw/", int(params["NB_ARTICLES_INDEX"]))
tags_full_list = list_directory("gen/tags")

# Generate html for each article (gen/ dir)
for filename in added_files+modified_files:
    try:
        with open(filename, 'r') as fh:
            article, title, date, author, tags = "", "", "", "", ""
            for line in fh.readlines():
                article += line
                if "@title=" in line:
                    title = line[line.find("@title=")+7:].strip()
                    continue
                if "@date=" in line:
                    date = line[line.find("@date=")+6:].strip()
                    continue
                if "@author=" in line:
                    author = line[line.find("@author=")+7:].strip()
                    continue
                if "@tags=" in line:
                    tags = line[line.find("@tags=")+6:].strip()
                    continue
    except IOError:
        print("[ERROR] An error occurred while generating article " +
              filename[4:]+".")

    if not isset("tags") or not isset("title") or not isset("author"):
        sys.exit("[ERROR] Missing parameters (title, author, date, tags) "
                 "in article "+filename[4:]+".")

    date_readable = ("Le "+date[0:2]+"/"+date[2:4]+"/"+date[4:8] +
                     " à "+date[9:11]+":"+date[11:13])
    day_aside = date[0:2]
    month_aside = months[int(date[2:4]) - 1]

    tags_comma = ""
    tags = [i.strip() for i in tags.split(",")]
    for tag in tags:
        if tags_comma != "":
            tags_comma += ", "

        tags_comma += ("<a href=\""+params["BLOG_URL"] +
                       "/tags/"+tag+".html\">"+tag+"</a>")

    # Markdown support
    if filename.endswith(".md"):
        article = markdown.markdown(gfm(article))

    # Write generated HTML for this article in gen /
    article = replace_tags(article, search_list, replace_list)

    # Handle @article_path
    article_path = params["BLOG_URL"] + "/" + date[4:8] + "/" + date[2:4]
    article = article.replace("@article_path", article_path)

    try:
        auto_dir("gen/"+filename[4:-5]+".gen")
        with open("gen/"+filename[4:-5]+".gen", 'w') as article_file:
            article_file.write("<article>\n"
                               "\t<aside>\n"
                               "\t\t<p class=\"day\">"+day_aside+"</p>\n"
                               "\t\t<p class=\"month\">"+month_aside+"</p>\n"
                               "\t</aside>\n"
                               "\t<div class=\"article\">\n"
                               "\t\t<header><h1 class=\"article_title\"><a " +
                               "href=\""+params["BLOG_URL"]+"/"+filename[4:] +
                               "\">"+title+"</a></h1></header>\n"
                               "\t\t"+article+"\n"
                               "\t\t<footer><p class=\"date\">"+date_readable +
                               "</p>\n"
                               "\t\t<p class=\"tags\">Tags : "+tags_comma +
                               "</p></footer>\n"
                               "\t</div>\n"
                               "</article>\n")
            print("[INFO] (GEN ARTICLES) Article "+filename[4:]+" generated")
    except IOError:
        sys.exit("[ERROR] An error occurred when writing generated HTML for "
                 "article "+filename[4:]+".")

# Starting to generate header file (except title)
tags_header = ""
for tag in sorted(tags_full_list, key=cmp_to_key(locale.strcoll)):
    with open("gen/tags/"+tag[9:-4]+".tmp", "r") as tag_fh:
        nb = len(tag_fh.readlines())

    tags_header += "<div class=\"tag\">"
    tags_header += ("<a href=\""+params["BLOG_URL"] +
                    "/tags/"+tag[9:-4]+".html\">")
    tags_header += ("/"+tag[9:-4]+" ("+str(nb)+")")
    tags_header += ("</a> ")
    tags_header += "</div>"
try:
    with open("raw/header.html", "r") as header_fh:
        header = header_fh.read()
except IOError:
    sys.exit("[ERROR] Unable to open raw/header.html file.")

header = header.replace("@tags", tags_header, 1)
header = header.replace("@blog_url", params["BLOG_URL"])
articles_header = ""
articles_index = ""

rss = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")

if os.path.isfile("raw/rss.css"):
    rss += ("<?xml-stylesheet type=\"text/css\" " +
            "href=\""+params["PROTOCOL"]+params["BLOG_URL"]+"/rss.css\"?>\n")


rss += ("<rss version=\"2.0\" xmlns:atom=\"http://www.w3.org/2005/Atom\" "
        "xmlns:content=\"http://purl.org/rss/1.0/modules/content/\">\n")
rss += ("\t<channel>"
        "\t\t<atom:link href=\""+params["PROTOCOL"]+params["BLOG_URL"] +
        "/rss.xml\" rel=\"self\" type=\"application/rss+xml\"/>\n"
        "\t\t<title>"+params["BLOG_TITLE"]+"</title>\n"
        "\t\t<link>"+params["PROTOCOL"] + params["BLOG_URL"]+"</link>\n"
        "\t\t<description>"+params["DESCRIPTION"]+"</description>\n"
        "\t\t<language>"+params["LANGUAGE"]+"</language>\n"
        "\t\t<copyright>"+params["COPYRIGHT"]+"</copyright>\n"
        "\t\t<webMaster>"+params["WEBMASTER"]+"</webMaster>\n"
        "\t\t<lastBuildDate>" +
        utils.formatdate(mktime(gmtime()))+"</lastBuildDate>\n")


# Generate header (except title) + index file + rss file
for i, article in enumerate(["gen/"+x[4:-5]+".gen" for x in last_articles]):
    content, title, tags, date, author = "", "", "", "", ""
    content_desc = ""
    try:
        with open(article, "r") as fh:
            for line in fh.readlines():
                content += line
                if "@title=" in line:
                    title = line[line.find("@title=")+7:].strip()
                    continue
                if "@date=" in line:
                    date = line[line.find("@date=")+6:].strip()
                    continue
                if "@author=" in line:
                    author = line[line.find("@author=")+7:].strip()
                    continue
                if "@tags=" in line:
                    tags = line[line.find("@tags=")+6:].strip()
                    continue
                content_desc += line
    except IOError:
        sys.exit("[ERROR] Unable to open "+article+" file.")

    if not isset("title"):
        sys.exit("[ERROR] No title found in article "+article[4:]+".")

    if i < 5:
        articles_header += "<li>"
        articles_header += ("<a href=\""+params["BLOG_URL"] + "/" +
                            article[4:-4]+".html\">"+title+"</a>")
        articles_header += "</li>"

    articles_index += content
    date_rss = utils.formatdate(mktime(gmtime(mktime(datetime.
                                                     datetime.
                                                     strptime(date,
                                                              "%d%m%Y-%H%M")
                                                     .timetuple()))))

    rss += ("\t\t<item>\n" +
            "\t\t\t<title>"+remove_tags(title)+"</title>\n" +
            "\t\t\t<link>"+params["PROTOCOL"]+params["BLOG_URL"]+"/" +
            article[4:-4]+".html</link>\n" +
            "\t\t\t<guid isPermaLink=\"true\">" +
            params["PROTOCOL"] + params["BLOG_URL"]+"/"+article[4:-4]+".html</guid>\n"
            # Apply remove_tags twice to also remove tags in @title and so
            "\t\t\t<description>" + truncate(remove_tags(remove_tags(replace_tags(get_text_rss(content_desc),
                                                                                  search_list,
                                                                                  replace_list)))) +
            "</description>\n" +
            "\t\t\t<content:encoded><![CDATA[" +
            replace_tags(get_text_rss(content),
                         search_list,
                         replace_list).replace('"'+params['BLOG_URL'],
                                               '"'+params['BLOG_URL_RSS']) +
            "]]></content:encoded>\n" +
            "\t\t\t<pubDate>"+date_rss+"</pubDate>\n" +
            ("\n".join(["\t\t\t<category>" + i.strip() + "</category>"
                        for i in tags.split(",")]))+"\n" +
            "\t\t\t<author>"+params["WEBMASTER"]+"</author>\n" +
            "\t\t</item>\n")


# Finishing header gen
articles_header += ("<li><a "+"href=\""+params["BLOG_URL"] +
                    "/archives.html\">"+"Archives</a></li>")
header = header.replace("@articles", articles_header, 1)

try:
    auto_dir("gen/header.gen")
    with open("gen/header.gen", "w") as header_gen_fh:
        header_gen_fh.write(header)
        print("[INFO] (HEADER) Header has been generated successfully.")
except FileNotFoundError:
    sys.exit("[ERROR] An error occurred while writing header file.")
except IOError:
    sys.exit("[ERROR] Unable to open gen/header.gen for writing.")

# Getting content from footer file
try:
    with open("raw/footer.html", "r") as footer_fh:
        footer = footer_fh.read()
        footer = footer.replace("@blog_url", params["BLOG_URL"])
except IOError:
    sys.exit("[ERROR] An error occurred while parsing footer "
             "file raw/footer.html.")

# Finishing index gen
index = (header.replace("@title", params["BLOG_TITLE"], 1) +
         articles_index + "<p class=\"archives\"><a "+"href=\"" +
         params["BLOG_URL"]+"/archives.html\">Archives</a></p>"+footer)

try:
    with open("blog/index.html", "w") as index_fh:
        index_fh.write(index)
        print("[INFO] (INDEX) Index page has been generated successfully.")
except IOError:
    sys.exit("[ERROR] Error while creating index.html file")
except IOError:
    sys.exit("[ERROR] Unable to open index.html file for writing.")

# Finishing rss gen
rss += "\t</channel>\n</rss>"

try:
    with open("blog/rss.xml", "w") as rss_fh:
        rss_fh.write(rss)
except IOError:
    sys.exit("[ERROR] An error occurred while writing RSS file.")

# Regenerate tags pages
for tag in tags_full_list:
    tag_content = header.replace("@title", params["BLOG_TITLE"] +
                                 " - "+tag[4:-4], 1)

    # Sort by date
    with open(tag, "r") as tag_gen_fh:
        articles_list = ["gen/"+line.replace(".html", ".gen").strip() for line
                         in tag_gen_fh.readlines()]
    articles_list.sort(key=lambda x: (get_date(x)[4:8], get_date(x)[2:4],
                                      get_date(x)[:2], get_date(x)[9:]),
                       reverse=True)

    for article in articles_list:
        with open(article.strip(), "r") as article_fh:
            tag_content += article_fh.read()

    tag_content += footer
    try:
        auto_dir(tag.replace("gen/", "blog/"))
        with open(tag.replace("gen/", "blog/")[:-4]+".html", "w") as tag_fh:
            tag_fh.write(tag_content)
            print("[INFO] (TAGS) Tag page for "+tag[9:-4] +
                  " has been generated successfully.")
    except IOError:
        sys.exit("[ERROR] An error occurred while generating tag page \"" +
                 tag[9:-4]+"\"")

# Finish generating HTML for articles (blog/ dir)
for article in added_files+modified_files:
    try:
        with open("gen/"+article[4:-5]+".gen", "r") as article_fh:
            content = article_fh.read()
    except IOError:
        sys.exit("[ERROR] An error occurred while opening"
                 "gen/"+article[4:-5]+".gen file.")

    for line in content.split("\n"):
        if "@title=" in line:
            title = line[line.find("@title=")+7:].strip()
            break

    content = header.replace("@title", params["BLOG_TITLE"] + " - " +
                             title, 1) + content + footer
    try:
        auto_dir("blog/"+article[4:])
        with open("blog/"+article[4:], "w") as article_fh:
            article_fh.write(content)
            print("[INFO] (GEN ARTICLES) HTML file generated in blog dir for "
                  "article "+article[4:]+".")
    except IOError:
        sys.exit("[ERROR] Unable to write blog/"+article[4:]+" file.")

# Regenerate pages for years / months
years_list.sort(reverse=True)
for i in years_list:
    try:
        int(i)
    except ValueError:
        continue

    # Generate pages per year
    page_year = header.replace("@title", params["BLOG_TITLE"]+" - "+i, 1)

    months_list.sort(reverse=True)
    for j in months_list:
        if not os.path.isdir("blog/"+i+"/"+j):
            continue

        # Generate pages per month
        page_month = header.replace("@title",
                                    params["BLOG_TITLE"]+" - "+i+"/"+j, 1)

        articles_list = list_directory("gen/"+i+"/"+j)
        articles_list.sort(key=lambda x: (get_date(x)[4:8], get_date(x)[2:4],
                                          get_date(x)[:2], get_date(x)[9:]),
                           reverse=True)

        for article in articles_list:
            try:
                with open(article, "r") as article_fh:
                    article_content = replace_tags(article_fh.read(),
                                                   search_list, replace_list)
                    page_month += article_content
                    page_year += article_content
            except IOError:
                sys.exit("[ERROR] Error while generating years and "
                         "months pages. Check your gen folder, you "
                         "may need to regenerate some articles. The "
                         "error was due to "+article+".")

        page_month += footer
        try:
            with open("blog/"+i+"/"+j+"/index.html", "w") as page_month_fh:
                page_month_fh.write(page_month)
        except IOError:
            sys.exit("[ERROR] Unable to write index file for "+i+"/"+j+".")

    page_year += footer
    try:
        with open("blog/"+i+"/index.html", "w") as page_year_fh:
            page_year_fh.write(page_year)
    except IOError:
        sys.exit("[ERROR] Unable to write index file for "+i+".")

# Generate archive page
archives = header.replace("@title", params["BLOG_TITLE"]+" - Archives", 1)

years_list = os.listdir("blog/")
years_list.sort(reverse=True)

archives += ("<article><div class=\"article\"><h1 " +
             "class=\"article_title\">Archives</h1><ul>")
for i in years_list:
    if not os.path.isdir("blog/"+i):
        continue

    try:
        int(i)
    except ValueError:
        continue

    archives += "<li><a href=\""+params["BLOG_URL"]+"/"+i+"\">"+i+"</a></li>"
    archives += "<ul>"

    months_list = os.listdir("blog/"+i)
    months_list.sort(reverse=True)
    for j in months_list:
        if not os.path.isdir("blog/"+i+"/"+j):
            continue

        archives += ("<li><a href=\""+params["BLOG_URL"] + "/" + i +
                     "/"+j+"\">"+datetime.datetime.
                     strptime(j, "%m").strftime("%B").title()+"</a></li>")
    archives += "</ul>"

archives += "</ul></div></article>"
archives += footer

try:
    with open("blog/archives.html", "w") as archives_fh:
        archives_fh.write(archives)
except IOError:
    sys.exit("[ERROR] Unable to write blog/archives.html file.")

# Include header and footer for pages that need it
for i in os.listdir("blog/"):
    if (os.path.isdir("blog/"+i) or i in ["header.html", "footer.html",
                                          "rss.xml", "style.css", "index.html",
                                          "archives.html", "humans.txt"]):
        continue

    if not i.endswith(".html"):
        continue

    with open("blog/"+i, 'r+') as fh:
        content = fh.read()
        fh.seek(0)

        if content.find("#include_header_here") != -1:
            content = content.replace("#include_header_here",
                                      header.replace("@title",
                                                     (params["BLOG_TITLE"] +
                                                      " - "+i[:-5].title()),
                                                     1),
                                      1)
            fh.write(content)
            fh.seek(0)

        if content.find("#include_footer_here") != -1:
            fh.write(content.replace("#include_footer_here", footer, 1))

os.system("git add --ignore-removal blog/ gen/")
