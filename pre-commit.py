#!/usr/bin/python

#TODO : gitignore

import sys
import shutil
import os
import datetime
import subprocess

def isset(variable):
	return variable in locals() or variable in globals()

def list_directory(path): 
    fichier=[] 
    for root, dirs, files in os.walk(path): 
        for i in files: 
            fichier.append(os.path.join(root, i)) 
    return fichier

def get_tags(fh):
	line = fh.readline()
	while "@tags=" not in line:
		line = fh.readline()
	if "@tags" not in line:
		return []
		
	line = line.strip() #Delete \n at the end of the line
	tag_pos = line.find("@tags=")
	tags = line[tag_pos+6:].split(",")
	return tags

def latest_articles(directory, number):
	now = datetime.datetime.now()
	counter = 0
	latest_articles = []

	for i in range(int(now.strftime('%Y')), 0, -1):
		if counter>=25:
			break

		if os.path.isdir(directory+"/"+str(i)):
			for j in range(12, 0, -1):
				if j<10:
					j = "0"+str(j)

				if os.path.isdir(directory+"/"+str(i)+"/"+str(j)):
					articles_list = list_directory(directory+str(i)+"/"+str(j))
					articles_list.sort(key=lambda x: os.stat(x).st_mtime) #Sort by date the articles

					latest_articles += articles_list[:number-counter]
					if len(latest_articles) < number-counter:
						counter+=len(articles_list)
					else:
						counter=25

	#Delete directory in file names
	return latest_articles	

def auto_dir(path):
	directory = os.path.dirname(path)
	try:
		if not os.path.exists(directory):
			os.makedirs(directory)
	except IOError:
		sys.exit("[ERROR] An error occured while creating "+path+" file and parent dirs.")

#Find the changes to be committed
try:
	#TODO : Check this command
	changes = subprocess.check_output(["git", "diff", "--cached", "--name-status"], universal_newlines=True)
except:
	sys.exit("[ERROR] An error occured when running git diff.")

#Fill lists for modified, deleted and added files
modified_files = []
deleted_files = []
added_files = []

changes = changes.strip().split("\n")
if changes == [""]:
	sys.exit("[ERROR] Nothing to do...")

for changed_file in changes:
	if changed_file[0] == "A":
		added_files.append(changed_file[changed_file.index("\t")+1:])
	elif changed_file[0] == "M":
		modified_files.append(changed_file[changed_file.index("\t")+1:])
	elif changed_file[0] == "D":
		deleted_files.append(changed_file[changed_file.index("\t")+1:])
	else:
		sys.exit("[ERROR] An error occured when running git diff.")

#Only keep modified raw articles files
for filename in list(added_files):
	if filename[:4] != "raw/":
		added_files.remove(filename)
	
	try:
		int(filename[4:8])
	except ValueError:
		added_files.remove(filename)

for filename in list(modified_files):
	if filename[:4] != "raw/":
		modified_files.remove(filename)
	
	try:
		int(filename[4:6])
	except ValueError:
		modified_files.remove(filename)

for filename in list(deleted_files):
	if filename[:4] != "raw/":
		deleted_files.remove(filename)
	
	try:
		int(filename[4:6])
	except ValueError:
		deleted_files.remove(filename)



print("[INFO] Added files : "+", ".join(added_files))
print("[INFO] Modified files : "+", ".join(modified_files))
print("[INFO] Deleted filed : "+", ".join(deleted_files))

print("[INFO] Updating tags for added and modified files")
for filename in added_files:
	try:
		with open(filename, 'r') as fh:
			tags = get_tags(fh)
			if len(tags) > 0:
				for tag in tags:
					try:
						auto_dir("gen/tags/"+tag+".tmp")
						with open("gen/tags/"+tag+".tmp", 'a+') as tag_file:
							tag_file.seek(0)
							if filename[4:] not in tag_file.read():
								tag_file.write(filename[4:]+"\n") 
							print("[INFO] (TAGS) Found tag "+tag+" for article "+filename[4:])
					except IOError:
						sys.exit("[ERROR] (TAGS) New tag found but error occured in article "+filename[4:]+": "+tag+".")
			else:
				sys.exit("[ERROR] (TAGS) In added article "+filename[4:]+" : No tags found !")
	except IOError:
		sys.exit("[ERROR] Unable to open file "+filename+".")

for filename in modified_files:
	try:
		with open(filename, 'r') as fh:
			tags = get_tags(fh)
			if(len(tags)) > 0:
				for tag in list_directory("gen/tags/"):
					try:
						with open(tag, 'r+') as tag_file:
							if tag[tag.index("tags/") + 5:tag.index(".tmp")] in tags and filename[4:] not in tag_file.read():
									tag_file.seek(0, 2) #Append to end of file
									tag_file.write(filename[4:]+"\n")
									print("[INFO] (TAGS) Found new tag "+tag[:tag.index(".tmp")]+" for modified article "+filename[4:])
									tags.remove(tag_file[9:])
							if tag[tag.index("tags/") + 5:tag_index(".tmp")] not in tags and filename[4:] in tag_file.read():
									old_tag_file_content = tag_file.read()
									tag_file.truncate()
									tag_file.write(old_tag_file_content.replace(filename[4:]+"\n", ""))
									print("[INFO] (TAGS) Deleted tag "+tag[:tag.index(".tmp")]+" in modified article "+filename[4:])
									tags.remove(tag_file[9:])
					except IOError:
						sys.exit("[ERROR] (TAGS) An error occured when parsing tags of article "+filename[4:]+".")

				for tag in tags: #New tags added
					try:
						auto_dir("gen/tags/"+tag+".tmp")
						with open("gen/tags/"+tag+".tmp", "a+") as tag_file:
							tag_file.write(filename[4:]+"\n")
							print("[INFO] (TAGS) Found new tag "+tag+" for modified article "+filename[4:])
					except IOError:
						sys.exit("[ERROR] (TAGS) An error occured when parsing tags of article "+filename[4:]+".")
			else:
				sys.exit("[ERROR] (TAGS) In modified article "+filename[4:]+" : No tags found !")
	except IOError:
		sys.exit("[ERROR] Unable to open file "+filename+".")

#Delete tags for deleted files and delete all generated files
for filename in deleted_files:
	try:
		with open(filename, 'r') as fh:
			tags = get_tags(fh)
			if len(tags) > 0:
				for tag in tags:
					try:
						with open("gen/tags/"+tag+".tmp", 'r+') as tag_file:
							old_tag_file_content = tag_file.read()
							tag_file.truncate()
							#Delete file in tag
							tag_file.write(old_tag_file_content.replace(filename[4:]+"\n", ""))
					except IOError:
						sys.exit("[ERROR] An error occured while deleting article "+filename[4:]+" from tags files.")
			else:
				sys.exit("[ERROR] (TAGS) In deleted article "+filename[4:]+" : No tags found !")
	except IOError:
		sys.exit("[ERROR] Unable to open file "+filename+".")

	#Delete generated files
	try:
		os.unlink("gen/"+filename[4:-5]+".gen")
		os.unlink("blog/"+filename[4:])
	except FileNotFoundError:
		print("[INFO] Article "+filename[4:]+" was not already generated. You should check manually.")
	
	print("[INFO] Deleted article "+filename[4:]+" in both gen and blog directories")

#Delete empty tags files 
for tag in list_directory("gen/tags"):
	try:
		with open(tag, 'r') as tag_file:
			content = tag_file.read().strip()
		if content == '':
			try:
				os.unlink(tag)
				os.unlink(tag.replace("gen", "blog"))
			except FileNotFoundError:
				print("[INFO] "+tag+" was found to be empty but there was an error during deletion. You should check manually.")
			print("[INFO] (TAGS) No more article with tag "+tag[8:-4]+", deleting it.")
	except IOError:
		sys.exit("[ERROR] Unable to open "+tag+".")

#(Re)Generate HTML files
for filename in added_files+modified_files:
	try:
		with open(filename, 'r') as fh:
			#Generate HTML for the updated articles
			for line in fh.readlines():
				if "@title=" in line:
					line = line.strip()
					title_pos = line.find("@title=")
					title = line[title_pos+7:]
					continue
				
				if "@date=" in line:
					line = line.strip()
					date_pos = line.find("@date=")
					date = line[date_pos+6:]
					continue
				
				if isset("date") and isset("title"):
					break

			fh.seek(0)
			article = fh.read()
			date = "Le "+date[0:2]+"/"+date[2:4]+"/"+date[4:8]+" à "+date[9:11]+":"+date[11:13]

			try:
				auto_dir("gen/"+filename[4:-5]+".gen")
				with open("gen/"+filename[4:-5]+".gen", 'w') as article_file:
					article_file.write("<article><nav class=\"aside_article\"></nav><div class=\"article\"><h1>"+title+"</h1>"+article+"<p class=\"date\">"+date+"</p></div>\n")
					print("[GEN ARTICLES] Article "+filename[4:]+" generated")
			except IOError:
				print("[GEN ARTICLES ERROR] An error occurred while generating article "+filename[4:])
	except IOError:
		sys.exit("[ERROR] Unable to open file "+filename+".")	

#Generate headers file (except title)
try:
	with open("raw/header.html", "r") as header_fh:
		#Tags
		tags = list_directory("gen/tags")
		header = header_fh.read()
		tags_header = "<ul>"
		for tag in tags:
			tags_header += "<li><a href=\""+tag[4:-4]+".html\">"+tag[9:-4]+"</a></li>"
		tags_header += "</ul>"
		header = header.replace("@categories", tags_header, 1)

		#Articles
		latest_articles_list = latest_articles("gen/", 5)
		articles_header = "<ul>"
		for article in latest_articles_list:
			try:
				with open(article, 'r') as fh:
					line = fh.readline()
					while "@title" not in line:
						line = fh.readline()
					line = line.strip()
					title_pos = line.find("@title=")
					title = line[title_pos+7:]

					articles_header += "<li><a href=\""+article[4:-4]+".html\">"+title+"</a></li>"
			except IOError:
				sys.exit("[ERROR] Unable to open file "+article+".")
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
except IOError:
	sys.exit("[ERROR] Unable to open raw/header.html file.")

#Generate footer file
if not os.path.isfile("raw/footer.html"):
	sys.exit("[ERROR] (FOOTER) Footer file (raw/footer.html) not found.")
try:
	shutil.copy("raw/footer.html", "gen/footer.gen")
	print("[INFO] (FOOTER) Footer has been generated successfully")
except IOError:
	sys.exit("[ERROR] Unable to copy the footer.html file.")

#Regenerate index file
last_25_articles = latest_articles("gen/", 25)
try:
	auto_dir("blog/index.html")
	with open("blog/index.html", "w") as index_fh:
		try:
			with open("gen/header.gen", "r") as header_gen_fh:
				index = header_gen_fh.read()
			for article in last_25_articles:
				with open(article, "r") as article_fh:
					index += article_fh.read()
			with open("gen/footer.gen") as footer_gen_fh:
				index += footer_gen_fh.read()
			index_fh.write(index)
			print("[INFO] (INDEX) Index page has been generated successfully.")
		except IOError:
			sys.exit("[ERROR] Error while creating index.html file")
except IOError:
	sys.exit("[ERROR] Unable to open index.html file for writing.")

#Regenerate tags pages
for tag in list_directory("gen/tags"):
	try:
		auto_dir(tag.replace("gen/", "blog/"))
		with open(tag.replace("gen/", "blog/"), "w") as tag_fh:
			with open(tag, "r") as tag_gen_fh:
				with open("gen/header.gen", "r") as header_fh:
					tag_content = header_fh.read()
					tag_content.replace("<title>@titre</title", "<title>"+tag[4:-4]+"</title>")
				tag_gen_fh_lines = tag_gen_fh.readlines()
				for line in tag_gen_fh_lines:
					line = line.replace(".html", ".gen")
					with open("gen/"+line.strip(), "r") as article_handler:	
						tag_content += article_handler.read()
				with open("gen/footer.gen", "r") as footer_handler:
					tag_content += footer_handler.read()
			tag_fh.write(tag_content)
			print("[INFO] (TAGS) Tag page for "+tag+" has been generated successfully.")
	except IOError:
		sys.exit("[ERROR] An error occured while generating tag page \""+tag[9:-4]+"\"")

#Finish articles pages generation
for filename in added_files+modified_files:
	try:
		auto_dir("blog/"+filename[4:])
		with open("blog/"+filename[4:], "w") as article_fh:
			with open("gen/header.gen", "r") as header_gen_fh:
				article = header_gen_fh.read()
			with open("gen/"+filename[4:-5]+".gen", "r") as article_gen_fh:
				article += article_gen_fh.read()
			with open("gen/footer.gen", "r") as footer_gen_fh:
				article += footer_gen_fh.read()
			article_fh.write(article)
			print("[INFO] (ARTICLES) Article page for "+filename[4:]+" has been generated successfully.")
	except IOError:
		sys.exit("[ERROR] An error occured while generating article "+filename[4:]+" page.")

#Generate RSS
#TODO
