Blogit
======

A git based blogging software. Just as Jekyll and so, it takes your articles as html files and computes them to generate static page and RSS feed to serve behind a webserver. It uses git as a backend file manager (as git provide some useful features like history and hooks) and Python for scripting the conversion process. You can customize the python scripts to handle special tags (ie, not standard HTML tags) just as &lt;code&gt; for example. See params file in raw dir to modify this.

This project is still a WIP.

How it works ?
==============

There are three directories under the tree : raw for your raw HTML articles and header/footer, gen (created by the script) for the temporary generated files and blog for the blog folder to serve behind the webserver.

Articles must be in folders year/month/ARTICLE.html (ARTICLE is whatever you want) and some extras comments must be put in the article file for the script to handle it correctly. See the test.html example file for more info on how to do it.

You can put a file in "wait mode" and don't publish it yet, just by adding .ignore at the end of its filename; Every file that you put in raw and that is not a .html file is just copied at the same place in the blog dir (to put images in your articles, for example, just put them beside your articles and make a relative link in your HTML article).

You should change the params file (raw/params) before starting to correctly set your blog url, your email address and the blog title (among other parameters).

When you finish editing an article, just git add it and commit. The pre-commit.py hook will run automatically and generate your working copy.

Note about tags : Tags are automatically handled and a page for each tag is automatically generated. A page with all the articles for each month and each year is also automatically generated.

Note : Don't remove gen/ content unless you know what you're doing. These files are temporary files for the blog generation but they are useful to regenerate the RSS feed for example. If you delete them, you may need to regenerate them.

Important note : This is currently a beta version and the hook isn't set to run automatically for now. You have to manually run pre-commit.py (or move it to .git/hooks but this has never been tested ^^).

Example of syntax for an article
================================
```HTML
<!--
	@tags=*** //put here the tags for your article, comma-separated list
	@titre=***i //Title for your article
	@author=Phyks //Name of the author (not displayed by now)
	@date=23062013-1337 //Date in the format DDMMYYYY-HHMM
->
<article content> (== Whatever you want)</article>
```

LICENSE
=======

* --------------------------------------------------------------------------------
* "THE NO-ALCOHOL BEER-WARE LICENSE" (Revision 42):
* Phyks (webmaster@phyks.me) wrote this file. As long as you retain this notice you
* can do whatever you want with this stuff (and you can also do whatever you want
* with this stuff without retaining it, but that's not cool...). If we meet some 
* day, and you think this stuff is worth it, you can buy me a soda (--beer--) in 
* return.
*																		Phyks
* ---------------------------------------------------------------------------------
