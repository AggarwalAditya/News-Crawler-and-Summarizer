#!c:/Python27/python.exe
# print("Content-type: text/html")
print("""
	<TITLE>Database  Connection</TITLE>
""")
import MySQLdb
import requests
from bs4 import BeautifulSoup
from readability import ParserClient
import re
from subprocess import *
import os

def summarization():
    pass

def generate_content(url,category):
    parser_client = ParserClient(token='7c8daeedd7726bf0c7d6b042098ee320ae336d87')
    parser_response = parser_client.get_article(str(url))
    article = parser_response.json()
    str_article_title=article['title']
    strarticle = article['content']
    final_article = re.sub('<.*?>', '', strarticle)
    final_article2 = re.sub('&.*?;', '', final_article)

    line = re.sub('["]', '', final_article2)
    final_article3=line.encode('utf-8').strip()
    final_article3=os.linesep.join([s for s in final_article3.splitlines() if s])
    final_article4=re.sub(' +',' ',final_article3)
    linet=re.sub('["]', '', str_article_title)
    final_article_title = linet.encode('utf-8').strip()


    intcategory=int(category)
    db = MySQLdb.connect("localhost", 'root', '', "TESTDB")
    cursor = db.cursor()
    try:
        sql='INSERT INTO meta_content(article_content,link,main_category_id,article_title)VALUES("%s","%s","%d","%s")'%(final_article4,url,intcategory,final_article_title)

        cursor.execute(sql)

        db.commit()
        db.close()
    except:
        db.rollback()
        db.close()


    summarization()


def jarWrapper(*args):
    process = Popen(['java', '-jar']+list(args), stdout=PIPE, stderr=PIPE)
    ret = []
    while process.poll() is None:
        line = process.stdout.readline()
        if line != '' and line.endswith('\n'):
            ret.append(line[:-1])
    stdout, stderr = process.communicate()
    ret += stdout.split('\n')
    if stderr != '':
        ret += stderr.split('\n')
    ret.remove('')
    return ret

def crawl_google_trends(url):
    args = ['Fin2.jar', url]
    result = jarWrapper(*args)
    interm = []
    for i in range(0, len(result)):
        if (i % 2 != 0):
            interm.append(result[i])

    interm2 = []
    for i in range(0, len(interm)):
        var = re.sub('[\r]', '', interm[i])
        interm2.append(str(var))

    db = MySQLdb.connect("localhost", 'root', '', "TESTDB")  # to check for similarity between links
    c = db.cursor()
    sql1 = " SELECT * FROM `post_management`"
    c.execute(sql1)
    result1 = c.fetchall()
    db.close()
    post_managment_url_list = []
    for row in result1:
        post_managment_url_list.append(row[8])


    final=[]

    for g in range(0, len(interm2)):
        flag = 1
        var=interm2[g]
        for e in range(0, len(post_managment_url_list)):
            if post_managment_url_list[e] == var:
                db = MySQLdb.connect("localhost", 'root', '', "TESTDB")
                cur = db.cursor()
                sqlstat = "UPDATE post_management SET Count_Duplicate=Count_Duplicate+1 WHERE Post_Url='%s'" % (
                post_managment_url_list[e])
                try:
                    cur.execute(sqlstat)
                    db.commit()
                    db.close()
                except:
                    db.rollback()
                    db.close()
                flag = 0
                break
        if flag == 1:
            final.append(var)

    return final


def crawl_google_news(url):
    source_code = requests.get(url)
    plain_text = source_code.text
    soup = BeautifulSoup(plain_text, "html.parser")

    mylist = []
    for k in soup.findAll('a', {'target': '_blank'}):
        href = k.get('href')
        strhref = str(href)
        mylist.append(strhref)

    db = MySQLdb.connect("localhost", 'root', '', "TESTDB")  # to check for similarity between links
    c = db.cursor()
    sql1 = " SELECT * FROM `post_management`"
    c.execute(sql1)
    result1 = c.fetchall()
    db.close()
    post_managment_url_list = []
    for row in result1:
        post_managment_url_list.append(row[8])

    final = []

    for i in range(0, len(mylist)):
        flag = 1
        if mylist[i] == "None":
            var = mylist[i - 1]
            for e in range(0, len(post_managment_url_list)):
                if post_managment_url_list[e] == var:
                    db = MySQLdb.connect("localhost", 'root', '', "TESTDB")
                    cur=db.cursor()
                    sqlstat="UPDATE post_management SET Count_Duplicate=Count_Duplicate+1 WHERE Post_Url='%s'" % (post_managment_url_list[e])
                    try:
                        cur.execute(sqlstat)
                        db.commit()
                        db.close()
                    except:
                        db.rollback()
                        db.close()
                    flag = 0
                    break
            if flag == 1:
                final.append(var)
    return final


def check(url,news_substring,trends_substring):
    if news_substring in url:
        return 1
    else:
        return 2



def crawl(links,main_category,count):
    print("Generating Links")

    for p in range(0,len(links)):
        print("Fetching "+links[p])
        url = str(links[p])

        news_substring="news.google.co.in/news"
        trends_substring="www.google.co.in/trends"
        return_val=check(url,news_substring,trends_substring)

        #final=[]
        if(return_val==1):
            final=crawl_google_news(url)
        else:
            final=crawl_google_trends()


        for j in range(0,len(final)):
            db = MySQLdb.connect("localhost", 'root', '', "TESTDB")  # to check for story count
            c = db.cursor()
            sql1 = " SELECT * FROM `post_management` WHERE Category_id=%d"% main_category[p]
            c.execute(sql1)
            result1 = c.fetchall()
            db.close()
            if(len(result1)==count[p]):
                break
            else:
                print(final[j] + " " + str(main_category[p]) + " ")
                generate_content(final[j], main_category[p])


def read_database():
    print("Reading database")
    try:
        db = MySQLdb.connect("localhost", 'root', '', "TESTDB")
        cursor = db.cursor()
        sql1 = "SELECT * FROM `sites` WHERE Active=1"
        sql2 = "SELECT * FROM `site_category` WHERE Active=1"
        cursor.execute(sql1)
        results_sites = cursor.fetchall()

        cursor.execute(sql2)
        results_site_category=cursor.fetchall()
        db.close()

        links=[]
        for row in results_sites:
            site_link = row[2]
            links.append(site_link)

        main_category=[]
        count=[]
        for row in results_site_category:
            main_category_id=row[4]
            story_count=row[5]
            main_category.append(main_category_id)
            count.append(story_count)

        for i in range(0,len(links)):
            print(links[i]+" "+str(main_category[i])+" "+str(count[i]))
        print("Finished reading the database")
        crawl(links,main_category,count)
        print("I am back")


    except:
        print("Error: unable to fecth data from sites table")


read_database()