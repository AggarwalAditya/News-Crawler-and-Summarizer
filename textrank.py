import io
import nltk
import itertools
from operator import itemgetter
import networkx as nx
import os
import MySQLdb
from similarity import get_similarity
import time
# apply syntactic filters based on POS tags
def filter_for_tags(tagged, tags=['NN', 'JJ', 'NNP']):
    return [item for item in tagged if item[1] in tags]


def normalize(tagged):
    return [(item[0].replace('.', ''), item[1]) for item in tagged]


def unique_everseen(iterable, key=None):

    seen = set()
    seen_add = seen.add
    if key is None:
        for element in itertools.ifilterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                yield element


def lDistance(firstString, secondString):
    "Function to find the Levenshtein distance between two words/sentences - gotten from http://rosettacode.org/wiki/Levenshtein_distance#Python"
    if len(firstString) > len(secondString):
        firstString, secondString = secondString, firstString
    distances = range(len(firstString) + 1)
    for index2, char2 in enumerate(secondString):
        newDistances = [index2 + 1]
        for index1, char1 in enumerate(firstString):
            if char1 == char2:
                newDistances.append(distances[index1])
            else:
                newDistances.append(1 + min((distances[index1], distances[index1 + 1], newDistances[-1])))
        distances = newDistances
    return distances[-1]


def buildGraph(nodes):
    "nodes - list of hashables that represents the nodes of the graph"
    gr = nx.Graph()  # initialize an undirected graph
    gr.add_nodes_from(nodes)
    nodePairs = list(itertools.combinations(nodes, 2))

    # add edges to the graph (weighted by Levenshtein distance)
    for pair in nodePairs:
        firstString = pair[0]
        secondString = pair[1]
        levDistance = lDistance(firstString, secondString)
        gr.add_edge(firstString, secondString, weight=levDistance)

    return gr


def extractKeyphrases(text):
    # tokenize the text using nltk
    wordTokens = nltk.word_tokenize(text)

    # assign POS tags to the words in the text
    tagged = nltk.pos_tag(wordTokens)
    textlist = [x[0] for x in tagged]

    tagged = filter_for_tags(tagged)
    tagged = normalize(tagged)

    unique_word_set = unique_everseen([x[0] for x in tagged])
    word_set_list = list(unique_word_set)

    # this will be used to determine adjacent words in order to construct keyphrases with two words

    graph = buildGraph(word_set_list)

    # pageRank - initial value of 1.0, error tolerance of 0,0001,
    calculated_page_rank = nx.pagerank(graph, weight='weight')

    # most important words in ascending order of importance
    keyphrases = sorted(calculated_page_rank, key=calculated_page_rank.get, reverse=True)

    # the number of keyphrases returned will be relative to the size of the text (a third of the number of vertices)
    aThird = len(word_set_list) / 3
    keyphrases = keyphrases[0:aThird + 1]

    # take keyphrases with multiple words into consideration as done in the paper - if two words are adjacent in the text and are selected as keywords, join them
    # together
    modifiedKeyphrases = set([])
    dealtWith = set([])  # keeps track of individual keywords that have been joined to form a keyphrase
    i = 0
    j = 1
    while j < len(textlist):
        firstWord = textlist[i]
        secondWord = textlist[j]
        if firstWord in keyphrases and secondWord in keyphrases:
            keyphrase = firstWord + ' ' + secondWord
            modifiedKeyphrases.add(keyphrase)
            dealtWith.add(firstWord)
            dealtWith.add(secondWord)
        else:
            if firstWord in keyphrases and firstWord not in dealtWith:
                modifiedKeyphrases.add(firstWord)

            # if this is the last word in the text, and it is a keyword,
            # it definitely has no chance of being a keyphrase at this point
            if j == len(textlist) - 1 and secondWord in keyphrases and secondWord not in dealtWith:
                modifiedKeyphrases.add(secondWord)

        i = i + 1
        j = j + 1

    return modifiedKeyphrases


def extractSentences(text):
    sent_detector = nltk.data.load('tokenizers/punkt/english.pickle')
    sentenceTokens = sent_detector.tokenize(text.strip())
    graph = buildGraph(sentenceTokens)

    calculated_page_rank = nx.pagerank(graph, weight='weight')

    # most important sentences in ascending order of importance
    sentences = sorted(calculated_page_rank, key=calculated_page_rank.get, reverse=True)

    # return a 100 word summary
    summary = ' '.join(sentences)
    summaryWords = summary.split()
    summaryWords = summaryWords[0:101]
    summary = ' '.join(summaryWords)

    return summary


def writeFiles(summary, keyphrases, fileName,title,cat_name,art_main,art_url,art_stat,dup_id,dup_count):
    "outputs the keyphrases and summaries to appropriate database tables"
    db = MySQLdb.connect("localhost", 'root', '', "inswipes")
    cursor = db.cursor()
    print("Generating " + 'keywords for article ' + str(fileName) + '\n')


    keyphrase_total=""
    for keyphrase in keyphrases:
        keyphrase_temp=keyphrase
        keyphrase_temp2=keyphrase_total
        keyphrase_total=keyphrase_temp2 + keyphrase_temp + ", "


    print("Generating " + 'summary for article ' + str(fileName) + '\n')

    try:
        article_date=time.strftime("%Y-%m-%d")
        article_time=time.strftime("%H:%M:%S")
        sql_insert = 'INSERT INTO `post_management`(`Date`, `Time`, `Title`, `Category_Name`, `Main_Article`, `Summary`, `Keywords`, `Post_Url`, `Status`, `Post_Id_Duplicate`, `Count_Duplicate`) VALUES("%s","%s","%s","%s","%s","%s","%s","%s","%d","%d","%d")'%(article_date, article_time, title, cat_name, art_main, summary, keyphrase_total, art_url, art_stat, dup_id, dup_count)
        cursor.execute(sql_insert)
        db.commit()
    except:
        db.rollback()

    db.close()
# retrieve each of the articles

def main_summarizer():
    counter = 0;
    db = MySQLdb.connect("localhost", 'root', '', "inswipes")
    cursor = db.cursor()

    sql1 = "SELECT * FROM `meta_content` WHERE post_id=(SELECT MAX(post_id) from `meta_content`)"
    cursor.execute(sql1)

    resultset = cursor.fetchall()
    row = resultset[0]

    article_number = row[0]

    text = row[1]

    article_link = row[2]
    article_category = row[3]
    article_title = row[4]
    article_status = 0
    duplicate_id = 0
    duplicate_counter = 0
    print text + '\n'

    sql2 = 'SELECT Main_Article FROM `post_management` WHERE Category_Name="%d"' % (article_category)
    cursor.execute(sql2)
    resultset2 = cursor.fetchall()

    print('Reading article ' + str(article_number) + '\n')

    keyphrases = extractKeyphrases(text)

    summary = extractSentences(text)

    #Checks whether there are articles of similar category present. If Yes , then checks whether it is a duplicate article or not, if No, inserts it.

    if resultset2:
        print ("Same category articles are present\n")
        for row in resultset2:
            article_check = row[0]
            duplication_factor = get_similarity(text, article_check)
            print duplication_factor
            if duplication_factor > 0.6:
                print ("Article is Duplicate")
                counter=1
            else:
                print ("Article is not Duplicate")

        if counter == 0:
            writeFiles(summary, keyphrases, article_number, article_title, article_category, text, article_link,
                       article_status, duplicate_id, duplicate_counter)
        else:
            print ("Article found Duplicate to a previous one, Hence insertion not conducted")

    else:
        print ("no\n")
        writeFiles(summary, keyphrases, article_number, article_title, article_category, text, article_link,
                   article_status, duplicate_id, duplicate_counter)

    db.close()

