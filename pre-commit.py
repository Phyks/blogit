#!/usr/bin/python

# TODO : Replace \ for line-breaking ?
# TODO : Orthographe dans les messages d'erreur
# TODO : What happens when a file is moved with git ?
# TODO : Test the whole thing
# TODO : What happens when I run it as a hook ?
# TODO : What happens when I commit with -a option ?
# TODO : Harmonize messages and erros

import sys
import getopt
import shutil
import os
import datetime
import subprocess
import re

from time import gmtime, strftime, mktime


# Test if a variable exists (== isset function in PHP)
def isset(variable):
    return variable in locals() or variable in globals()


# List all files in path directory
# Works recursively
# Return files list with path relative to current dir
def list_directory(path):
    fichier = []
    for root, dirs, files in os.walk(path):
        for i in files:
            fichier.append(os.path.join(root, i))
    return fichier


# Return a list with the tags of a given article (fh)
def get_tags(fh):
    tag_line = ''
    for line in fh.readlines():
        if "@tags=" in line:
            tag_line = line
            break

    if not tag_line:
        return []

    tags = [x.strip() for x in line[line.find("@tags=")+6:].split(",")]
    return tags


# Return the number latest articles in dir directory
def latest_articles(directory, number):
    now = datetime.datetime.now()
    counter = 0
    latest_articles = []

    for i in range(int(now.strftime('%Y')), 0, -1):
        if counter >= number:
            break

        if os.path.isdir(directory+"/"+str(i)):
            for j in range(12, 0, -1):
                if j < 10:
                    j = "0"+str(j)

                if os.path.isdir(directory+"/"+str(i)+"/"+str(j)):
                    articles_list = list_directory(directory+str(i)+"/"+str(j))
                    # Sort by date the articles
                    articles_list.sort(key=lambda x: os.stat(x).st_mtime)

                    latest_articles += articles_list[:number-counter]
                    if len(latest_articles) < number-counter:
                        counter += len(articles_list)
                    else:
                        counter = number
    return latest_articles


# Auto create necessary directories to write a file
def auto_dir(path):
    directory = os.path.dirname(path)
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except IOError:
        sys.exit("[ERROR] An error occured while creating "+path+" file "
                 "and parent dirs.")


# Replace some user specific syntax tags (to repplace smileys for example)
def replace_tags(article, search_list, replace_list):
    return_string = article
    for search, replace in zip(search_list, replace_list):
        return_string = re.sub(search, replace, article)
    return return_string


try:
    opts, args = getopt.gnu_getopt(sys.argv, "hf", ["help", "force-regen"])
except getopt.GetoptError:
    sys.exit("Error while parsing command line arguments. "
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
try:
    with open("raw/params", "r") as params_fh:
        params = {}
        for line in params_fh.readlines():
            if line.strip() == "" or line.strip().startswith("#"):
                continue
            option, value = line.split("=", 1)
            if option == "SEARCH":
                search_list = value.strip().split(",")
            elif option == "REPLACE":
                replace_list = value.strip().split(",")
            else:
                params[option.strip()] = value.strip()
except IOError:
    sys.exit("[ERROR] Unable to load raw/params file which defines important "
             "parameters. Does such a file exist ? See doc for more info "
             "on this file.")


# Fill lists for modified, deleted and added files
modified_files = []
deleted_files = []
added_files = []

if not force_regen:
    # Find the changes to be committed
    try:
        changes = subprocess.check_output(["git", "diff", "--cached", "--name-status"], universal_newlines=True)
    except:
        sys.exit("[ERROR] An error occured when fetching file changes "
                 "from git.")

    changes = changes.strip().split("\n")
    if changes == [""]:
        sys.exit("[ERROR] Nothing to do... Did you had new files with "
                 "\"git add\" before ?")

    for changed_file in changes:
        if changed_file[0].startswith("A"):
            added_files.append(changed_file[changed_file.index("\t")+1:])
        elif changed_file[0].startswith("M"):
            modified_files.append(changed_file[changed_file.index("\t")+1:])
        elif changed_file[0].startswith("D"):
            deleted_files.append(changed_file[changed_file.index("\t")+1:])
        else:
            sys.exit("[ERROR] An error occured when running git diff.")
else:
    shutil.rmtree("blog/")
    shutil.rmtree("gen/")
    added_files = list_directory("raw")

if not added_files and not modified_files and not deleted_files:
    sys.exit("[ERROR] Nothing to do... Did you had new files with "
             "\"git add\" before ?")

# Only keep modified raw articles files
for filename in list(added_files):
    direct_copy = False

    if not filename.startswith("raw/"):
        added_files.remove(filename)
        continue

    try:
        int(filename[4:8])
    except ValueError:
        direct_copy = True

    if ((not filename.endswith(".html") and not filename.endswith(".ignore"))
       or direct_copy):
        # Note : this deal with CSS, images or footer file
        print("[INFO] (Not HTML file) Copying directly not html file "
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

    if not filename.startswith("raw/"):
        modified_files.remove(filename)
        continue

    try:
        int(filename[4:6])
    except ValueError:
        direct_copy = True

    if ((not filename.endswith("html") and not filename.endswith("ignore"))
       or direct_copy):
        print("[INFO] (Not HTML file) Updating directly not html file "
              + filename[4:]+" to blog dir.")
        auto_dir("blog/"+filename[4:])
        shutil.copy(filename, "blog/"+filename[4:])
        modified_files.remove(filename)
        continue

    if filename.endswith("ignore"):
        print("[INFO] (Not published) Found not published article "
              + filename[4:-7]+".")
        added_files.remove(filename)
        continue

for filename in list(deleted_files):
    direct_copy = False

    if not filename.startswith("raw/"):
        deleted_files.remove(filename)
        continue

    try:
        int(filename[4:6])
    except ValueError:
        direct_copy = True

    if ((not filename.endswith("html") and not filename.endswith("ignore"))
       or direct_copy):
        print("[INFO] (Not HTML file) Copying directly not html file "
              + filename[4:]+" to blog dir.")
        auto_dir("blog/"+filename[4:])
        shutil.copy(filename, "blog/"+filename[4:])
        deleted_files.remove(filename)
        continue

    if filename.endswith("ignore"):
        print("[INFO] (Not published) Found not published article "
              + filename[4:-7]+".")
        added_files.remove(filename)
        continue


print("[INFO] Added files : "+", ".join(added_files))
print("[INFO] Modified files : "+", ".join(modified_files))
print("[INFO] Deleted filed : "+", ".join(deleted_files))

print("[INFO] Updating tags for added and modified files")
for filename in added_files:
    try:
        with open(filename, 'r') as fh:
            tags = get_tags(fh)
    except IOError:
        sys.exit("[ERROR] Unable to open file "+filename+".")

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
                     "occured in article "+filename[4:]+": "+tag+".")

for filename in modified_files:
    try:
        with open(filename, 'r') as fh:
            tags = get_tags(fh)
    except IOError:
        sys.exit("[ERROR] Unable to open file "+filename+".")

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
                    print("[INFO] (TAGS) Found new tag "+tag[:tag.index(".tmp")]+" for modified article "+filename[4:])
                    tags.remove(tag_file[9:])
                if (tag[tag.index("tags/") + 5:tag.index(".tmp")] not in tags
                   and filename[4:] in tag_file.read()):
                    tag_file_old_content = tag_file.read()
                    tag_file.truncate()
                    tag_file.write(tag_file_old_content.replace(filename[4:]+"\n", ""))
                    print("[INFO] (TAGS) Deleted tag "+tag[:tag.index(".tmp")]+" in modified article "+filename[4:])
                    tags.remove(tag_file[9:])
        except IOError:
            sys.exit("[ERROR] (TAGS) An error occured when parsing tags "
                     " of article "+filename[4:]+".")

    for tag in tags:  # New tags created
        try:
            auto_dir("gen/tags/"+tag+".tmp")
            with open("gen/tags/"+tag+".tmp", "a+") as tag_file:  # Delete tag file here if empty after deletion
                tag_file.write(filename[4:]+"\n")
                print("[INFO] (TAGS) Found new tag "+tag+" for "
                      "modified article "+filename[4:])
        except IOError:
            sys.exit("[ERROR] (TAGS) An error occured when parsing tags "
                     "of article "+filename[4:]+".")

# Delete tags for deleted files and delete all generated files
for filename in deleted_files:
    try:
        with open(filename, 'r') as fh:
            tags = get_tags(fh)
    except IOError:
        sys.exit("[ERROR] Unable to open file "+filename+".")

    if not tags:
        sys.exit("[ERROR] (TAGS) In deleted article "+filename[4:]+" : "
                 "No tags found !")

    for tag in tags:
        try:
            with open("gen/tags/"+tag+".tmp", 'r+') as tag_file:  # Delete tag file here if empty after deletion
                tag_file_old_content = tag_file.read()
                tag_file.truncate()
                # Delete file in tag
                tag_file_write = tag_file_old_content.replace(filename[4:]+"\n", "")
                if tag_file_write:
                    tag_file.write(tag_file_write)
        except IOError:
            sys.exit("[ERROR] An error occured while deleting article" +
                     filename[4:]+" from tags files.")

        if not tag_file_write:
            try:
                os.unlink(tag)
                print("[INFO] (TAGS) No more article with tag "+tag[8:-4]+", deleting it.")
            except FileNotFoundError:
                print("[INFO] "+tag+" was found to be empty but there was an error during deletion. You should check manually.")

    # Delete generated files
    try:
        os.unlink("gen/"+filename[4:-5]+".gen")
        os.unlink("blog/"+filename[4:])
    except FileNotFoundError:
        print("[INFO] Article "+filename[4:]+" seems to not have already been "
              "generated. You should check manually.")

    print("[INFO] Deleted article "+filename[4:]+" in both gen and blog "
          "directories")


# Common lists that are used multiple times
last_articles = latest_articles("raw/", int(params["NB_ARTICLES_INDEX"]))
tags_full_list = list_directory("gen/tags")

# Generate html for each article
for filename in added_files+modified_files:
    try:
        with open(filename, 'r') as fh:
            article = "", "", "", "", ""
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
        print("[ERROR] An error occurred while generating article "+filename[4:])

    if not isset("tags") or not isset("title") or not isset("author"):
        sys.exit("[ERROR] Missing parameters (title, author, date, tags) in article "+filename[4:]+".")

    date_readable = "Le "+date[0:2]+"/"+date[2:4]+"/"+date[4:8]+" à "+date[9:11]+":"+date[11:13]

    # Write generated HTML for this article in gen /
    article = replace_tags(article, search_list, replace_list)
    try:
        auto_dir("gen/"+filename[4:-5]+".gen")
        with open("gen/"+filename[4:-5]+".gen", 'w') as article_file:
            article_file.write("<article><nav class=\"aside_article\"></nav><div class=\"article\"><h1>"+title+"</h1>"+article+"<p class=\"date\">"+date+"</p></div>\n")
            print("[GEN ARTICLES] Article "+filename[4:]+" generated")
    except IOError:
        sys.exit("[ERROR] An error occured when writing generated HTML for article "+filename[4:]+".")

# Starting to generate header file (except title)
tags_header = "<ul>"
for tag in tags_full_list:
    tags_header += "<li><a href=\""+params["BLOG_URL"]+tag[4:-4]+".html\">"+tag[9:-4]+"</a></li>"
tags_header += "</ul>"
try:
    with open("raw/header.html", "r") as header_fh:
        header = header_fh.read()
except IOError:
    sys.exit("[ERROR] Unable to open raw/header.html file.")

header = header.replace("@tags", tags_header, 1)
header = header.replace("@blog_url", params["BLOG_URL"], 1)
articles_header = "<ul>"
articles_index = "<ul>"

# Generate header (except title) + index file
del title
for i, article in enumerate(last_articles):
    try:
        with open(article, "r") as fh:
            for line in fh.readlines():
                if "@title=" in line:
                    title = line[line.find("@title=")+7:].strip()
                    break
    except IOError:
        sys.exit("[ERROR] Unable to open "+article+" file.")

    if not isset("title"):
        sys.exit("[ERROR] No title found in article "+article[4:]+".")

    if i < 5:
        articles_header += "<li><a href=\""+params["BLOG_URL"]+article[4:-4]+".html\">"+title+"</a></li>"

    articles_index += "<li><a href=\""+params["BLOG_URL"]+article[4:-4]+".html\">"+title+"</a></li>"

# Finishing header gen
articles_header += "</ul>"
header = header.replace("@articles", articles_header, 1)

try:
    auto_dir("gen/header.gen")
    with open("gen/header.gen", "w") as header_gen_fh:
        header_gen_fh.write(header)
        print("[INFO] (HEADER) Header has been generated successfully.")
except FileNotFoundError:
    sys.exit("[ERROR] (HEADER) An error occured while writing header file.")
except IOError:
    sys.exit("[ERROR] Unable to open gen/header.gen for writing.")

# Getting content from footer file
try:
    with open("raw/footer.html", "r") as footer_fh:
        footer = footer_fh.read()
except IOError:
    sys.exit("[ERROR] An error occured while parsing footer file raw/footer.html.")

# Finishing index gen
articles_index += "</ul>"
index = header.replace("@title", params["BLOG_TITLE"], 1) + articles_index + footer

try:
    with open("blog/index.html", "w") as index_fh:
        index_fh.write(index)
        print("[INFO] (INDEX) Index page has been generated successfully.")
except IOError:
    sys.exit("[ERROR] Error while creating index.html file")
except IOError:
    sys.exit("[ERROR] Unable to open index.html file for writing.")

# Regenerate tags pages
for tag in tags_full_list:
    tag_content = header.replace("@title", params["BLOG_TITLE"]+" - "+tag[4:-4], 1)

    with open(tag, "r") as tag_gen_fh:
        for line in tag_gen_fh.readlines():
            line = line.replace(".html", ".gen")
            with open("gen/"+line.strip(), "r") as article_fh:
                tag_content += article_fh.read()

    tag_content += footer
    try:
        auto_dir(tag.replace("gen/", "blog/"))
        with open(tag.replace("gen/", "blog/")[:-4]+".html", "w") as tag_fh:
            tag_fh.write(tag_content)
            print("[INFO] (TAGS) Tag page for "+tag[9:-4]+" has been generated successfully.")
    except IOError:
        sys.exit("[ERROR] An error occured while generating tag page \""+tag[9:-4]+"\"")

# Finish articles pages generation
for filename in added_files+modified_files:
    try:
        auto_dir("blog/"+filename[4:])
        with open("blog/"+filename[4:], "w") as article_fh:
            with open("gen/header.gen", "r") as header_gen_fh:
                article = header_gen_fh.read()
            with open("gen/"+filename[4:-5]+".gen", "r") as article_gen_fh:
                line = article_gen_fh.readline()
                while "@title" not in line:
                    line = article_gen_fh.readline()
                line = line.strip()
                title_pos = line.find("@title=")
                title = line[title_pos+7:]
                article_gen_fh.seek(0)

                article = article.replace("@title", params["BLOG_TITLE"]+" - "+title, 1)
                article += replace_tags(article_gen_fh.read(), search_list, replace_list)
            with open("gen/footer.gen", "r") as footer_gen_fh:
                article += footer_gen_fh.read()
            article_fh.write(article)
            print("[INFO] (ARTICLES) Article page for "+filename[4:]+" has been generated successfully.")
    except IOError:
        sys.exit("[ERROR] An error occured while generating article "+filename[4:]+" page.")

#======================================
# Generate pages for each year and month
with open("gen/header.gen", "r") as header_gen_fh:
    header_gen = header_gen_fh.read()

with open("gen/footer.gen", "r") as footer_gen_fh:
    footer_gen = footer_gen_fh.read()

years_list = os.listdir("blog/")
years_list.sort(reverse=True)
for i in years_list:
    try:
        int(i)
    except ValueError:
        continue

    # Generate page per year
    page_year = header_gen.replace("@title", params["BLOG_TITLE"]+" - "+i, 1)

    months_list = os.listdir("blog/"+i)
    months_list.sort(reverse=True)
    for j in months_list:
        if not os.path.isdir("blog/"+i+"/"+j):
            continue

        # Generate pages per month
        page_month = header_gen.replace("@title", params["BLOG_TITLE"]+" - "+i+"/"+j, 1)

        articles_list = list_directory("gen/"+i+"/"+j)
        articles_list.sort(key=lambda x: os.stat(x).st_mtime, reverse=True)
        for article in articles_list:
            try:
                with open(article, "r") as article_fh:
                    article_content = replace_tags(article_fh.read(), search_list, replace_list)
                    page_month += article_content
                    page_year += article_content
            except IOError:
                sys.exit("[ERROR] Error while generating years and months pages. Check your gen folder, you may need to regenerate some articles. The error was due to "+article+".")

        page_month += footer_gen
        try:
            with open("blog/"+i+"/"+j+"/index.html", "w") as page_month_fh:
                page_month_fh.write(page_month)
        except IOError:
            sys.exit("[ERROR] Unable to write index file for "+i+"/"+j+".")

    page_year += footer_gen
    try:
        with open("blog/"+i+"/index.html", "w") as page_year_fh:
            page_year_fh.write(page_year)
    except IOError:
        sys.exit("[ERROR] Unable to write index file for "+i+".")


# Generate RSS
rss = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><rss version=\"2.0\" xmlns:atom=\"http://www.w3.org/2005/Atom\" xmlns:content=\"http://purl.org/rss/1.0/modules/content/\">"
rss += "<channel><atom:link href=\""+params["BLOG_URL"]+"rss.xml\" rel=\"self\" type=\"application/rss+xml\"/><title>"+params["BLOG_TITLE"]+"</title><link>"+params["BLOG_URL"]+"</link>"
rss += "<description>"+params["DESCRIPTION"]+"</description><language>"+params["LANGUAGE"]+"</language><copyright>"+params["COPYRIGHT"]+"</copyright>"
rss += "<webMaster>"+params["WEBMASTER"]+"</webMaster><lastBuildDate>"+strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())+"</lastBuildDate>"

for article in last_articles:
    del date, title
    try:
        with open(article, "r") as article_fh:
            tags = get_tags(article_fh)
            article_fh.seek(0)

            for line in article_fh.readlines():
                if "@title=" in line:
                    line = line.strip()
                    title_pos = line.find("@title=")
                    title = line[title_pos+7:].strip()
                    continue

                if "@date=" in line:
                    line = line.strip()
                    date_pos = line.find("@date=")
                    date = line[date_pos+6:].strip()
                    continue

                if isset("date") and isset("title"):
                    break

            date = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime(mktime(datetime.datetime.strptime(date, "%d%m%Y-%H%M").timetuple())))
            article_fh.seek(0)

            rss += "<item> \
                        <title>"+title+"</title> \
                        <link>"+params["BLOG_URL"]+article[5:]+"</link> \
                        <guid isPermaLink=\"false\">"+params["BLOG_URL"]+article[5:]+"</guid> \
                        <description><![CDATA["+replace_tags(article_fh.read(), search_list, replace_list)+"]]></description> \
                        <pubDate>"+date+"</pubDate> \
                        <category>"+', '.join(tags)+"</category> \
                        <author>"+params["WEBMASTER"]+"</author> \
                    </item>"
    except IOError:
        sys.exit("[ERROR] Unable to read article "+article+" to generate RSS file.")

rss += "</channel></rss>"

try:
    with open("blog/rss.xml", "w") as rss_fh:
        rss_fh.write(rss)
except IOError:
    sys.exit("[ERROR] An error occured while writing RSS file.")
