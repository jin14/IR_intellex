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
import string

stemmer = PorterStemmer()
termtfs = {}
def clean_query_nonphrasal(text):   
    output = []
    for query in text.split(' AND '):
        output.extend([stemmer.stem(i.lower()) for i in query.split() if  stemmer.stem(i.lower())])
    return output


def clean_query_phrasal(text):
    output = []
    for query in text.split(' AND '):
        result = [stemmer.stem(i.lower()) for i in query.split() if  stemmer.stem(i.lower())]
        output.append(result)
        
    return output

def tf(count):
	# calculate the logarithmic term frequency
    if count > 0:
        return 1 + math.log10(count)
    else:
        return 0

def L2norm(k):
	# compute the L2 norm of the term
    return math.sqrt(sum(map(lambda x:x**2 if x>0 else 0,k)))

def idf(docfreq,totaldocs):
    # compute the inverse document frequency score
    return math.log10(totaldocs/docfreq)

def queryscore_nonphrasal(query, d, total):
    queryD = Counter(query)
    L2 = L2norm(map(tf, queryD.values()))
    for term in queryD:
        if term in d['content']:
            #queryD[term] = (tf(queryD[term])/L2)* d['content'][term]['idf']
            queryD[term] = (tf(queryD[term]) * idf(len(d['content'][term], total))/L2)
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

#JW's code 
def mergeAND(left,right):
    bound = 4
    
    if len(left)<=bound and len(right)<=bound:
        result = []
        while len(left)!=0 and len(right)!=0:

            if left[0] == right[0]:
                result.append(left[0])
                left = left[1:]
                right = right[1:]

            elif left[0]>right[0]:
                right = right[1:]

            elif left[0]<right[0]:
                left = left[1:]
                
    else:
        result = skipintersectionAND(left,right)
    
    return result

#JW's code 
def skipintersectionAND(left,right):

# This method imitates the nature of a skiplist. The index will skip if it is a modulo of the (len(list))**0.5
# It is an intersection method. 

    i = 0
    j = 0
    skipI = math.floor(math.sqrt(len(left)))
    skipJ = math.floor(math.sqrt(len(right)))
    result = []
    
    while len(left)>i and len(right)>j:
        if left[i] == right[j]:
            result.append(left[i])
            i+=1
            j+=1
        elif left[i] < right[j]:
            if not bool(i%skipI) and i+skipI < len(left) and left[i+skipI] <= right[j]:
                while not bool(i%skipI) and i+skipI < len(left) and left[i+skipI] <= right[j]:
                    i+=skipI
            else:
                i+=1
        
        elif left[i] > right[j]:
            if not bool(j%skipJ) and j+skipJ < len(right) and left[i] >= right[j+skipJ]:
                while not bool(j%skipJ) and j+skipJ < len(right) and left[i] >= right[j+skipJ]:
                    j+=skipJ
            else:
                j+=1
        
    return result

def processQuery(query, dic, posting):
    listofdocs = []
    listofphrase = clean_query_phrasal(query)
    for phrase in listofphrase:
        if len(phrase) > 1:
            temp = getdocdict(phrase[0].keys())
            for term in phrase[1:]:
                temp = processOr(temp, getdocdict(term).keys())
            listofdocs.append(temp)
        else:
            listofdocs.append(getdocdict(phrase[0], dic, posting).keys())
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

def getdocdict(term, dic, posting):
    termtfs[term] = {}
    startOffset = dic['content'][term]['s']
    posting.seek(startOffset, 0)
    termdict = eval(posting.readline())
    for ids in termdict.keys():
        termtfs[term][ids] = termdict[ids]['tf']
    return termdict

def findLtcLnc(docId, listofterms, query_ltc):
    score = 0
    L2 = L2norm()
    for term in listofterms:
        ltc = query_ltc[term]
        lnc = termtfs[term][docId]
        score += (ltc * lnc)


def search(dictionary,postings,queries,output):
#   This is the main function that returns the query results and write it to the output file. 
#   It also has cachers instantiated to cache both the query results.
    d = json.load(open(dictionary,'r'))
    p = open(postings,'r')

    with open(queries) as q:
        with open(output,'w') as o:
            print("Querying...")
            for query in q.read().splitlines():
                docid = processQuery(query, d, p)
                #print ("non: " + str(query_n))
                query = query.replace('""', "")
                listofterms = clean_query_nonphrasal(query)
                listofphrase = [i for i in clean_query_phrasal(query) if len(i) > 1]
                query_ltc = queryscore_nonphrasal(query, d, len(d['docids']))
                result = {}
                docids = processQuery(query, d, p)
                heap = []
                for doc in docids:
                    score = findLtcLnc(doc, listofterms, query_ltc)
                    for phrase in listofphrase:
                        score *= phrasalQuery(phrase, d, p, doc)
                    heapq.heappush(heap, [score, doc])
                # get the top 10 document id based on the lnc.ltc score # need to use another method to determine output
                result = heapq.nlargest(40, heap)
                result = [(key, value) for value, key in result]
                result = ' '.join(map(str,[i[0] for i in result]))
                print("results: " + result)
                o.write(result + '\n')
                                           
    p.close()

# method to check if the 2 words are next to each other in the same document
# parses in the 2 postings of the 2 queried words. 
# pass in the list of docID that contains term A and B (found using MergeAnd method)
# then within each doc, check if A and B are next to each other
def phrasalQuery(term1, term2, docIDs, dic, pFile):
    print("################# commencing phrasal query now ################")
    postingsResultsList = []

    for id in docIDs:
        #fetch the positional indices from posting file
        start = dic['content'][term1]['s']
        pFile.seek(start, 0)
        #list of pos of term1 in docID id.
        r1 = pFile.readline()
        r1 = eval(r1) #convert to python dictionary form

        #is this the correct way to fetch the positional index?
        positions1 = r1[id]['index']

        start = dic['content'][term2]['s']
        pFile.seek(start, 0)
        #list of pos of term2 in docID id.
        r2 = pFile.readline()
        r2 = eval(r2)
        positions2 = r2[id]['index']

        print(positions1)
        print(type(positions1))
        print(positions2)
        print(type(positions2))

        k = 0
        while(k < len(positions1)):
            l = 0
            while(l < len(positions2)):
                #abs or strictly 1? can't even test when my indexing has issue =.=
                dist = abs(positions1[k] - positions2[l])
                print("dist:" +str(dist))
                if (dist == 1):
                    postingsResultsList.append(l)
                    print(postingsResultsList)
                elif (positions2[l] > positions1[k]):
                    break
                l += 1        
            for item in postingsResultsList:
                dist = abs(positions2[item] - positions1[k])
                if (dist > 1):
                    postingsResultsList.remove(item)
                k += 1         
    print ("############### lalala: " + str(postingsResultsList) + "##############")
    return postingsResultsList           





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
print("Time taken: " + str(end-start))

#