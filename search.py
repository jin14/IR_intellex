import heapq
from collections import Counter
from nltk.stem.porter import PorterStemmer
from util import tf,L2norm,idf
import os
import nltk
import json
import math
import sys
import getopt
import time
import string

stemmer = PorterStemmer()


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

def queryscore_nonphrasal(query,d):
    queryD = Counter(query)
    L2 = L2norm(map(tf,queryD.values()))
    for term in queryD:
        if term in d['content']:
            queryD[term] = (tf(queryD[term])/L2)* d['content'][term]['idf']
        else:
            queryD[term] = 0
            
    return queryD

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

def search(dictionary,postings,metadata,queries,output):


#   This is the main function that returns the query results and write it to the output file. 
#   It also has cachers instantiated to cache both the query results.

    d = json.load(open(dictionary,'r'))
    p = open(postings)
    m = open(metadata)

    with open(queries) as q:
        with open(output,'w') as o:
            print("Querying...")
            for query in q.read().splitlines():
                query = query.replace('"', ' ') #remove the quotation
                query = clean_query_nonphrasal(query)
                query_ltc = queryscore_nonphrasal(query,d)
                
                result = {}
                docids = sorted(d['docids'])
                for term in query:
                    if term in d['content']:
                        new = list(d['content'][term].keys())
                        new.remove('idf')
                        new = sorted(map(int,new))
                        docids = mergeAND(docids,new) # the key idf will be present
                
                docids = map(str,docids)
                for term in query:
                    for docid in docids:
                        try:
                            if docid in d['content'][term].keys():
                                if docid not in result:
                                    result[docid] = d['content'][term][docid]['tf'] * query_ltc[term]

                                else:
                                    result[docid] += d['content'][term][docid]['tf'] * query_ltc[term]
                        except:
                            continue            
                
                heap = [(value, key) for key,value in result.items()]
                # get the top 10 document id based on the lnc.ltc score # need to use another method to determine output
                result = heapq.nlargest(10, heap)
                result = [(key,value) for value, key in result]
                result = ' '.join(map(str,[i[0] for i in result]))
                o.write(result + '\n')
                                           
    p.close()

# method to check if the 2 words are next to each other in the same document
# parses in the 2 postings of the 2 queried words. 
# (have to seek using the 'start' and 'len' in d[content][term][docID])
# where to call this? and must retrieve query terms pair by pair ah?
def phrasalQuery(term1, term2, dictionary_file, postings_file):
    dic = json.load(open(dictionary,'r'))
    pFile = open(posting_file, "r+")
    #remove the prev 2 lines if we were to call this method in search()

    ans = []
    i = 0
    j = 0
    while (i < len(dic['content']['term1']) and j < len(dic['content']['term2'])):
        docid1 = dic['content']['term1']
        docid2 = dic['content']['term2']
        if (docid1 == docid2):
            postingsResultsList = []

            start = dic['content']['term1']['docid1']['start']
            length = dic['content']['term1']['docid1']['len']
            pFile.seek(start, 0)
            postings1 = pFile.read(length)

            start = dic['content']['term2']['docid2']['start']
            length = dic['content']['term2']['docid2']['len']
            pFile.seek(start, 0)
            postings2 = pFile.read(length)

            k = 0
            while(k < len(postings1)):
                l = 0
                while(l < len(postings2)):
                    dist = abs(postings1[k] - postings2[l])
                    if (dist == 1):
                        postingsResultsList.append(l)
                    elif (postings2[l] > postings1[k]):
                        break
                    l += 1        
                for item in postingsResultsList:
                    dist = abs(postings2[item] - postings1[k])
                    if (dist > 1):
                        postingsResultsList.remove(item)
                for item in postingsResultsList:
                    ans.append({"doc_id:" : docid1, "positionalData1:" : postings1[k], "positionalData2:" : postings2[item]})

                k += 1
            i += 1
            j += 1
        else: #document id not equal              
            if (docid1 < docid2):
                i += 1
            else:
                j += 1

    return ans            





def usage():
    print ("usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -m metadata-file -q file-of-queries -o output-file-of-results")

dictionary_file = postings_file = file_of_queries = output_results = metadata_file = None
try:
    opts, args = getopt.getopt(sys.argv[1:], 'd:p:m:q:o:')
except (getopt.GetoptError, err):
    usage()
    sys.exit(2)
for o, a in opts:
    if o == '-d':
        dictionary_file = a
    elif o == '-p':
        postings_file = a
    elif o == '-m':
    	metadata_file = a
    elif o == '-q':
        file_of_queries = a
    elif o == '-o':
        output_results = a
    else:
        assert False, "unhandled option"
if dictionary_file == None or postings_file == None or file_of_queries == None or output_results == None or metadata_file == None:  
    usage()
    sys.exit(2)

start = time.time()
search(dictionary_file,postings_file,metadata_file,file_of_queries,output_results)
end = time.time()
print("Time taken: " + str(end-start))
