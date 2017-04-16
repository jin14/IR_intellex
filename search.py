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
p = None

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

def queryscore_nonphrasal(query,d):
    queryD = Counter(query)
    L2 = L2norm(map(tf,queryD.values()))
    for term in queryD:
        if term in d['content']:
            #queryD[term] = (tf(queryD[term])/L2)* d['content'][term]['idf']
            queryD[term] = (tf(queryD[term])/L2)
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


def search(dictionary,postings,queries,output):


#   This is the main function that returns the query results and write it to the output file. 
#   It also has cachers instantiated to cache both the query results.
    global p
    d = json.load(open(dictionary,'r'))
    p = open(postings,'r')

    with open(queries) as q:
        with open(output,'w') as o:
            print("Querying...")
            for query in q.read().splitlines():
                query = query.replace('"', ' ') #remove the quotation
                query = clean_query_nonphrasal(query)
                query_ltc = queryscore_nonphrasal(query,d)
                
                result = {}
                phrasalList = []
                termtfs = {}
                docids = sorted(map(int,d['docids']))
                for term in query:
                    if term in d['content']:
                        print(term)
                        #new = list(d['content'][term].keys())\
                        offset = d['content'][term]['s']
                        p.seek(offset, 0)
                        termFound = p.readline() #this returns a string, not a dict
                        termFound = eval(termFound) # in dictionary form
                        idsForTerm = termFound.keys()
                        new = sorted(map(int,idsForTerm)) 
                        docids = processAnd(docids,new) # the key idf will be present
                        #docids = mergeAND(docids,new)
                        termtfs[term] = {}
                        for ids in idsForTerm:
                            termtfs[term][ids] = termFound[ids]['tf']


                # docids = map(str,docids)

                for term in query:
                    for docid in list(docids):
                        # print("current docid: " + docid)
                        try:
                            if docid in termtfs[term].keys():
                                if docid not in result:
                                    result[docid] = termtfs[term][docid] #* query_ltc[term]

                                else:
                                    result[docid] += termtfs[term][docid] #* query_ltc[term]
                        except:
                            continue            

                heap = [(value, key) for key,value in result.items()]
                # get the top 10 document id based on the lnc.ltc score # need to use another method to determine output
                result = heapq.nlargest(10, heap)
                result = [(key,value) for value, key in result]
                result = ' '.join(map(str,[i[0] for i in result]))
                print("results: " + result)
                o.write(result + '\n')
                                           
    p.close()

# method to check if the 2 words are next to each other in the same document
# parses in the 2 postings of the 2 queried words. 
# pass in the  list of docID that contains term A and B (found using MergeAnd method)
# then within each doc, check if A and B are next to each other
def phrasalQuery(term1, term2, docIDs, pFile):
    postingsResultsList = []

    for id in docIDs:
        #fetch the positional indices from posting file
        start = dic['content'][term1]['s']
        pFile.seek(start, 0)
        #list of pos of term1 in docID id.
        r1 = pFile.readLine()
        
        #is this the correct way to fetch the positional index?
        positions1 = r1['index']

        start = dic['content'][term2]['s']
        pFile.seek(start, 0)
        #list of pos of term2 in docID id.
        r2 = pFile.readLine()
        positions2 = r2['index']

        k = 0
        while(k < len(positions1)):
            l = 0
            while(l < len(positions2)):
                #abs or strictly 1? can't even test when my indexing has issue =.=
                dist = abs(positions1[k] - positions2[l])
                if (dist == 1):
                    postingsResultsList.append(l)
                elif (positions2[l] > positions1[k]):
                    break
                l += 1        
            for item in postingsResultsList:
                dist = abs(positions2[item] - positions1[k])
                if (dist > 1):
                    postingsResultsList.remove(item)
                k += 1         

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
search(dictionary_file,postings_file,file_of_queries,output_results)
end = time.time()
print("Time taken: " + str(end-start))

#