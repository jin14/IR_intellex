import heapq
from collections import Counter
from nltk.stem.porter import PorterStemmer
import os
import nltk
import json
import math
import sys
import getopt
import time
from time import gmtime, strftime
import string
from itertools import chain
from nltk.corpus import wordnet

stemmer = PorterStemmer()
termtfs = {}
termDict ={}
othermetadata = {}
synonymsList = []

#method to check if the two positions are next to each other.
#utilises the processAnd function
def processPhrasal(positions1, positions2):
    result = []

    positions1 = list(map(lambda x:x+1, positions1))
    result = processAnd(positions1, positions2)
    return result

#method to check if the phrase appears in the document
#list is the phrase, dic, pFile is dictionary&postings, id is the id of doc to be checked.
def phrasalQuery(list, dic, pFile, id):
    #a phrase only contains 2/3 words.
    resultsList = []
    length = len(list)
    if(length == 2):
        r1 = getdocdict(list[0], dic, pFile)
        
        r2 = getdocdict(list[1], dic, pFile)
        
        try:
            #list of pos of term1 in docID id.
            positions1 = r1[id]['index']
        except KeyError:
            positions1 = []    
            #list of pos of term2 in docID id.
        try:    
            positions2 = r2[id]['index']
        except KeyError:
            positions2 = []    
        postingsResultsList = processPhrasal(positions1, positions2)
    
    if(length == 3):
        r1 = getdocdict(list[0], dic, pFile)
        try:
            positions1 = r1[id]['index']
        except KeyError:
            positions1 = []
        r2 = getdocdict(list[1], dic, pFile)
        try:    
            positions2 = r2[id]['index']
        except KeyError:
            positions2 = []
        r3 = getdocdict(list[2], dic, pFile)
        try:
            #list of pos of term3 in docID id.
            positions3 = r3[id]['index']
        except KeyError:
            positions3 = []
        resultsList = processPhrasal(positions1, positions2)
        resultsList = processPhrasal(resultsList, positions3)
    #compute tf now
    freq = len(resultsList)

    phrasalQueryTF = tf(freq)
    return phrasalQueryTF  

#pre-process the non-phrasal version of the query. words are stored individually into a list.
def clean_query_nonphrasal(text):   
    output = []
    for query in text.split(' AND '):
        output.extend([stemmer.stem(i.lower()) for i in query.split() if  stemmer.stem(i.lower())])
    return output

#pre-process the phrasal version of the query. Phrase/word delimited by 'AND' will be stored in a list
def clean_query_phrasal(text):
    output = []
    for query in text.split(' AND '):
        result = [stemmer.stem(i.lower()) for i in query.split() if  stemmer.stem(i.lower())]
        output.append(result)
        
    return output

def clean_query_heuristic(query):
    result = []
    for phrase in query.split(' AND '):
        words = phrase.split() # split by space
        words = [stemmer.stem(word.lower()) for word in words] # stem and lowercase the tags
        
        result.append(' '.join(words))
        
    return result

#utility function
def tf(count):
	# calculate the logarithmic term frequency
    if count > 0:
        return 1 + math.log10(count)
    else:
        return 0
#utility function
def L2norm(k):
	# compute the L2 norm of the term
    return math.sqrt(sum(map(lambda x:x**2 if x>0 else 0,k)))
#utility function
def idf(docfreq,totaldocs):
    # compute the inverse document frequency score
    return math.log10(totaldocs/docfreq)

#computes the lnc.ltc
def queryscore_nonphrasal(query, d, total):
    queryD = Counter(query)
    
    L2 = L2norm(map(tf, queryD.values()))
    for term in queryD:
        
        if term in d['content']:
            #queryD[term] = (tf(queryD[term])/L2)* d['content'][term]['idf']
            queryD[term] = (tf(queryD[term]) * idf(len(d['content'][term]), total)/L2)
            if term in synonymsList:
                #synonym; half the tf
                queryD[term] *= 0.5
        else:
            queryD[term] = 0
     

    return queryD

#From our homework 2 code    
def processAnd(posting1, posting2):
    results = []
    i = 0
    j = 0
    while i < len(posting1) and j < len(posting2):
            if posting1[i] == posting2[j]:
                
                results.append(posting1[i])
                i += 1
                j += 1
            elif posting1[i] > posting2[j]:
                skip = int(math.sqrt(len(posting2)))
                
                if j % skip == 0 and (j+skip) < len(posting2):
                    if posting1[i]> posting2[j+skip]:
                        #print "skip"
                        j+= skip
                    else:    
                        j += 1
                else:
                    j += 1            
            else:
                skip = int(math.sqrt(len(posting1)))
                
                if i % skip == 0 and (i+skip) < len(posting1):
                    if posting2[j]> posting1[i+skip]:
                        #print "skip"
                        i+= skip
                    else:        
                        i += 1 
                else:
                    i += 1  
    #print( "merge? " + str(results))               
    return results

#process the query by getting the phrases (delimited by 'AND'),
#retrieve the document ids for the phrases
#if length of phrase > 1, 
def processQuery(query, dic, posting):
    listofdocs = []
    listofphrase = clean_query_phrasal(query)
    for phrase in listofphrase:
        temp = list(getdocdict(phrase[0], dic, posting).keys())
        if len(phrase) > 1:
            for term in phrase[1:]:
                temp = processOr(temp, list(getdocdict(term, dic, posting).keys()))
            listofdocs.append(temp)
        else:
            listofdocs.append(temp)
    results = listofdocs[0]
    for docs in listofdocs[1:]:
        results = processAnd(results, docs)

    return results

def processOr(posting1, posting2):
    results = []
    i = 0
    j = 0
    while i <= len(posting1) and j <= len(posting2):
        if i == len(posting1):  # if we reached the end of posting1, we append the rest of posting2 to the results
            results += posting2[j:]
            break
        elif j == len(posting2):  # if we reached the end of posting1, we append the rest of posting1 to the results
            results += posting1[i:]
            break
        elif posting1[i] == posting2[j]:  # if they have the same ID, append and increment both pointers
            results.append(posting1[i])
            i += 1
            j += 1
        elif posting1[i] > posting2[j]:  # if posting1 is larger, append and increment pointer j
            results.append(posting2[j])
            j += 1
        else:  # posting2 is larger, append and increment pointer i
            results.append(posting1[i])
            i += 1
    return results
#retrieve the document ids and corresponding tfs of the term
#from postings file, return in the form of python dictionary.
def getdocdict(term, dic, posting):

    if term in termDict:
        return termDict[term]

    termtfs[term] = {}
    try:
        startOffset = dic['content'][term]['s']
    except KeyError:
        return termtfs[term]
    posting.seek(startOffset, 0)
    termdict = eval(posting.readline())
    for ids in termdict.keys():
        termtfs[term][ids] = termdict[ids]['tf']

    termDict[term] = termdict    
    return termdict



#compute the lnc.ltc score
def findLtcLnc(docId, listofterms, query_ltc):
    score = 0
    #print(listofterms)
    for term in listofterms:
        try:
            ltc = query_ltc[term]
            lnc = termtfs[term][docId]
        except KeyError:
            lnc = 0    
        score += (ltc * lnc)


    return score
#computes the score multiplier for the date_posted
#the closer the date_posted to the current date, the higher the multiplier    
def computeDateMultiplier(diff):
    mul = 0
    if diff < 180:
        mul = 1.2
    elif (180 < diff and diff < 360):
        mul = 1.15
    elif (360<diff and diff<720):
        mul = 1.1
    elif (720<diff and diff<1080):
        mul = 1.05    
    else:
        mul = 1

    return mul

# gets a list of synonyms of the term using nltk wordnet.
# This is used when the term in the query is not found in the dictionary.
def getSynonymsList(term):
    synonyms = wordnet.synsets(term)
    synonymsList = list(chain.from_iterable([word.lemma_names() for word in synonyms]))
    return synonymsList

def search(dictionary,postings,queries,output):
#   This is the main function that returns the query results and write it to the output file. 
#   It also has cachers instantiated to cache both the query results.
    d = json.load(open(dictionary,'r'))
    p = open(postings,'r')
    metadata = d['metadata'] # get metadata (date posted, juristication, court)
    usefulAreaOfLaw = []
    usefulTags = []
    now = strftime("%Y-%m-%d", gmtime())
    now = now.replace('-', "")
    

    #get list of keys for dict of tags & areaoflaw
    areaoflaw = list(d['areaoflaw'].keys())
    tags = list(d['tags'].keys())  
    tag_areaoflaw = areaoflaw+tags

    with open(queries) as q:
        with open(output,'w') as o:
            #print("Querying...")
            for query in q.read().splitlines():
                query = query.replace('"', "")
                
                listofterms = clean_query_nonphrasal(query)
                finalList = list(listofterms)
                for t in listofterms:
                    if t not in d['content']:
                        finalList.extend(getSynonymsList(t))


                listofphrase = [i for i in clean_query_phrasal(query) if len(i) > 1]

                #the listofphrases below is for heuristic consideration
                #stores the entire phrase as an element in the list
                listofphrases = clean_query_heuristic(query)
                for phrase in tag_areaoflaw:

                    if phrase in listofphrases:
                        #if found in the query, find all docs that has that in postings
                        if phrase in areaoflaw:
                            offset = d['areaoflaw'][phrase]['start']
                            p.seek(offset, 0)
                            usefulAreaOfLaw = eval(p.readline())
                        if phrase in tags:                            
                            offset = d['tags'][phrase]['start']
                            p.seek(offset, 0)
                            usefulTags = list(eval(p.readline()))
                            
                query_ltc = queryscore_nonphrasal(finalList, d, len(d['docids']))
                result = {}
                docids = processQuery(query, d, p)
                heap = []
                for doc in docids:
                    score = findLtcLnc(doc, finalList, query_ltc)

                    for phrase in listofphrase:
                        score += phrasalQuery(phrase, d, p, doc)

                    #if juristication is singapore, we deem the document as being more important
                    juryList = list(metadata[str(doc)]['jury']) 
                    for jury in juryList:
                        if jury == "SG":
                            score *= 1.2


                    #view the doc being more relevant if the doc id has the areaoflaw (present in query)
                    for ids in usefulAreaOfLaw:
                        if (doc == ids):                    
                            score *= 1.25

                    for ids in usefulTags:
                        if (doc == ids):                    
                            score *= 1.2

                    #check dateposted
                    date = str(metadata[str(doc)]['date_posted'])
                    date = date.replace('-', "")
                    diff = int(now) - int(date)
                    mul = computeDateMultiplier(diff)
                    score *= mul
                    heap.append([score, doc])  
                # get the top 40 document id based on the lnc.ltc score # need to use another method to determine output
                result = sorted(heap, key=lambda x: x[0], reverse=True)
                

                a = sum([i[0] for i in result])
                
                if(len(result) > 0):
                	mean = a/len(result)
                else:
                	mean = 0
                result = ' '.join(map(str,[i[1] for i in result if i[0] >= mean]))
                #result = result[:int((len(result)/4))]
                #print(len([i[1] for i in result]))
                #result = ' '.join(map(str,[i[1] for i in result]))
                o.write(result + '\n')
                                           
    p.close()




def usage():
    print ("usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results")

dictionary_file = postings_file = file_of_queries = output_results = None
try:
    opts, args = getopt.getopt(sys.argv[1:], 'd:p:q:o:')
except getopt.GetoptError as err:
    usage()
    sys.exit(2)
for o, a in opts:
    if o == '-d':
        dictionary_file = a
    elif o == '-p':
        postings_file = a
    elif o == '-q':
        file_of_queries = a
    elif o == '-o':
        output_results = a
    else:
        assert False, "unhandled option"
if dictionary_file == None or postings_file == None or file_of_queries == None or output_results == None:  
    usage()
    sys.exit(2)

start = time.time()
search(dictionary_file, postings_file, file_of_queries, output_results)
end = time.time()

# python search.py -d finaldict.txt -p finalpost.txt -q query.txt -o output.txt
