Blogit
======

This script aims at building a static blog above a git repo. This way, you can
use git abilities to have full archives and backups of your blog. Many scripts
aims at doing this, and this is just one more. I needed something more personal
and fitted to my needs, so I came up with this code. It's not very beautiful,
can mostly be optimized but it's working for me. It may not be fitted to your
needs, but it's up to you to see it.

This script is just a python script that should be run as a git hook. You can
see a working version at http://phyks.me and the repository behind it is
publicly viewable at http://git.phyks.me/Blog. You should browse this
repository for example configuration and usage if you are interested by this
script.

This script has been developped by Phyks (phyks@phyks.me). For any suggestion
or remark, please send me an e-mail.

## Installation

1. Clone this repo.
2. Clear the .git directory and initialize a new empty git repo to store your
   blog.
3. Move the `pre-commit.py` script to `.git/hooks/pre-commit`
4. Edit the `raw/params` and edit it to fit your needs.
5. The `raw` folder comes with an example of blog architecture. Delete it and
   make your own.
6. You are ready to go !

## Params

Available options in `raw/params` are :

* `BLOG_TITLE` : The title of the blog, to display in the &lt;title&gt; element
  in rendered pages.
* `NB_ARTICLES_INDEX` : Number of articles to display on index page.
* `BLOG_URL` : Your blog base URL.
* `IGNORE_FILES` : A comma-separated list of files to ignore.
* `WEBMASTER` : Webmaster e-mail to put in RSS feed.
* `LANGUAGE` : Language param to put in RSS feed.
* `DESCRIPTION` : Blog description, for the RSS feed.
* `COPYRIGHT` : Copyright information, for the RSS feed.
* `SEARCH` : comma-separated list of elements to search for and replaced
  (custom regex, see code for more info)
* `REPLACE` : corresponding elements for replacement.

## Usage

This script will use three folders:

* `raw/` will contain your raw files
* `blog/` will contain the fully generated files to serve _via_ your http
  server
* `gen/` will store temporary intermediate files

All the files you have to edit are located in the `raw/` folder. It contains by
default an example version of a blog. You should start by renaming it and
making your own.

Articles can be edited in HTML directly or in Markdown. They must be located in
a `raw/year/month` folder, according to their date of publication and end with
.html for html articles and .md for markdown articles. The basic content of an
article is: ```` <!-- @author=AUTHOR_NAME @date=DDMMYYYY-HHMM @title=TITLE
@tags=TAGS --> CONTENT ````

where TAGS is a comma-separated list. Tags are automatically created if they do
not exist yet. The HTML comment *must* be at the beginning of the document and
is parsed to set the metadata of the article.

CONTENT is then either a HTML string or a markdown formatted one.

You can ignore an article to not make it publicly visible during redaction,
simply by adding a .ignore extension.


When you finish editing your article, you can add the files to git and commit,
to launch the script. You can also manually call the script with the
`--force-regen` option if you want to rebuild your entire blog.

## Header file

You can use the `@blog_url` syntax anywhere. It will be replaced by the URL of
the blog, as defined in the parameters (and this is useful to include CSS
etc.).

You can also use `@tags` that will be replaced by the list of tags and
`@articles` for the list of last articles.

## Static files

In static files, in raw folder (such as `divers.html` in the demo code), you
can use `#base_url` that will be replaced by the base url of the blog, as
defined in the parameters. This is useful to make some links.

## Alternatives

There exist many alternatives to this script, but they didn't fit my needs (and
were not all tested) :

* fugitive : http://shebang.ws/fugitive-readme.html
* Jekyll : http://jekyllrb.com/ and Oktopress : http://octopress.org/
* Blogofile : http://www.blogofile.com/

## LICENSE

    --------------------------------------------------------------------------------
    "THE NO-ALCOHOL BEER-WARE LICENSE" (Revision 42): Phyks
    (webmaster@phyks.me) wrote this file. As long as you retain this notice you
    can do whatever you want with this stuff (and you can also do whatever you
    want with this stuff without retaining it, but that's not cool...). If we
    meet some day, and you think this stuff is worth it, you can buy me a
    <del>beer</del> soda in return.  Phyks
    ---------------------------------------------------------------------------------
