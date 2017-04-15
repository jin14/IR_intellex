import string
from nltk.stem.porter import PorterStemmer
from nltk.tokenize import word_tokenize, sent_tokenize
import xml.etree.ElementTree as ET 
# from lxml import etree as ET
#import xml.etree.cElementTree as ET
import os
import json
import getopt
import sys
import time
from util import tf,L2norm,idf
import re
import multiprocessing
from multiprocessing import Pool

stemmer = PorterStemmer()

# class NoDaemonProcess(multiprocessing.Process):
#     # make 'daemon' attribute always return False
#     def _get_daemon(self):
#         return False
#     def _set_daemon(self, value):
#         pass
#     daemon = property(_get_daemon, _set_daemon)

# # We sub-class multiprocessing.pool.Pool instead of multiprocessing.Pool
# # because the latter is only a wrapper function, not a proper class.
# class MyPool(multiprocessing.pool.Pool):
#     Process = NoDaemonProcess

def storein_metadata(postings_file,metadata,index,key):
    
    index[key] = {}
    
    for term in metadata:
        start = postings_file.tell()
        postings = ','.join(map(str,metadata[term])) + '\n'
        postings_file.write(postings)
        index[key][term] ={'start': start}

    return index


def store_content1(posting_file,content,index,key):
    
    for term in content:
        
        start = posting_file.tell()
        postings = str(content[term]) + '\n'
        posting_file.write(postings)
    
        index[key][term] = {'s': start}

    return index


def store_title1(posting_file,title,index,key):
    
    for term in title:
        
        start = posting_file.tell()
        postings = str(title[term]) + '\n'
        posting_file.write(postings)
        
        index[key][term] = {'s':start}
    return index

def extract_info1(path):
    print(path)
    A_tags = {}
    A_content = {}
    A_title = {}
    tfs = {}
    A_areaoflaw = {}
    
    tree = ET.parse(path)
    
    docid = int(tree.find(".//str[@name='document_id']").text)
    date_posted = tree.find(".//date[@name='date_posted']").text[:10]
    title = tree.find(".//str[@name='title']").text
    content = tree.find(".//str[@name='content']").text
    
    court = [i.text for i in tree.findall(".//str[@name='court']")]
    jury = [i.text for i in tree.findall(".//arr[@name='jurisdiction']/str")]
    tag = [i.text for i in tree.findall(".//arr[@name='tag']/str")]
    areaoflaw = [i.text for i in tree.findall(".//arr[@name='areaoflaw']/str")]

    
    #court
    # subpool = MyPool()
    # result = subpool.starmap(addtodict,[(areaoflaw,docid),(tag,docid)])
    # subpool.close()
    # A_areaoflaw = result[0]
    # A_tags = result[1]

    A_areaoflaw = addtodict(areaoflaw,docid)
    A_tags = addtodict(tag,docid)
    
    #metadata
    A_metadata = {'jury':jury, 'court': court, 'date_posted': date_posted }
    
    #content
    content = clean_content(content)
    contentsize = len(content)
    
    for index,term in enumerate(content):
        if term not in A_content:
            A_content[term] = {docid:{'index':[index], 'tf':None}}
        
        else:
            if docid not in A_content[term]:
                A_content[term][docid] = {'index':[index],'tf':None}
                
            else:
                A_content[term][docid]['index'].append(index)
                
    length = []
    for term in A_content:
        if docid in A_content[term]:
            if term not in tfs:
                tfs[term] = {}
                tfreq = tf(len(A_content[term][docid]['index']))
                tfs[term][docid] = tfreq
                length.append(tfreq)
            
            else:
                tfreq = tf(len(A_content[term][docid]['index']))
                tfs[term][docid] = tfreq
                length.append(tfreq)
                
    
    norm = L2norm(length)
    for term in tfs:
        if docid in tfs[term]:
            tfs[term][docid] = tfs[term][docid]/norm
            
    
    for term in A_content:
        if docid in A_content[term]:
            A_content[term][docid]['tf'] = tfs[term][docid]
            
    
    #title
    for index,term in enumerate(title):
        if term not in A_title:
            A_title[term] = {docid:[index]}
        
        else:
            if docid not in A_title[term]:
                A_title[term][docid] = [index]
            else:
                A_title[term][docid].append(index)
                
    
    
    
    A_overall = {'content':A_content, 'title': A_title, 'metadata': A_metadata ,'docid':docid, 'tags': A_tags, 'areaoflaw': A_areaoflaw}
    
     
    
    
    return A_overall

def clean_content(text):
    
    chars = string.punctuation + '”' + '’' + '“' + '…'
    
    text = text.lower() #lowercase

    text = re.sub('[^A-Za-z0-9]+', ' ', text)
    
    # sub1 = MyPool()

    result = [sent for sent in sent_tokenize(text)]
    result = [word for sublist in result for word in word_tokenize(sublist)]


    # result = sub1.map(wordify,result)
    result = list(map(wordify,result))
    
    #sub1.close()
    

    return result



    
def stemmed_tags(tags):
    result = []
    for tag in tags:
        words = tag.split()
        words = [stemmer.stem(word.lower()) for word in words]
        
        result.append(' '.join(words))
        
    return result


    
def addtodict(texts,docid):
    dic = {}
    texts = stemmed_tags(texts)
    if len(texts)>1:
        for text in texts:
            if text in dic:
                dic[text].append(docid)
            else:
                dic[text] = [docid]
    elif len(texts)==1:
        text = texts[0]
        if text in dic:
            dic[text].append(docid)
        else:
            dic[text] = [docid]


    return dic

def merge_CT(A,B):
    
    for term in B: 
        if term in A:
            A[term].update(B[term])
        else:
            A[term] = B[term]
            
    return A

def mergerest(A,B):
    
    for term in B:
        if term in A:
            A[term].append(B[term])
        else:
            A[term] = B[term]
    
    return A

def mergerest_tags(A,B):
    
    for term in B:
        if term in A:
            A[term].extend(B[term])
        else:
            A[term] = B[term]
    
    return A


def wordify(word):
    chars = string.punctuation + '”' + '’' + '“' + '…'
    
    try:
        word = stemmer.stem(word).strip(chars)
    except:
        pass

    return word.strip(chars)

def make_dictionary1(directory,dictionary_file,postings_file):
    if directory[-1]!='/':
        directory = directory+'/'
        
    docids = []
    A_tags = {}
    A_dateposted = {}
    A_content = {}
    A_title = {}
    A_jury = {}
    A_court = {}
    tfs = {}
    A_areaoflaw = {}

    print("Scanning...")
    with os.scandir(directory) as theFiles:
        new = []
        for filename in theFiles:
            new.append(directory+filename.name)
            docids.append(filename.name[:-4])
            
    print("Extracting...")
    # pool = Pool()
    #pool = MyPool()
    num_workers = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(num_workers)
    chunksize = len(new)//(4*num_workers) + 1
    result = pool.map(extract_info1,new,chunksize)
    
    pool.close()
    
    print("Merging...")
    A_metadata = {}
    for i in result:
        A_content = merge_CT(A_content,i['content'])
        A_title = merge_CT(A_title,i['title'])
        A_areaoflaw = mergerest_tags(A_areaoflaw, i['areaoflaw'])
        A_tags = mergerest_tags(A_tags,i['tags'])
    
        A_metadata[i['docid']] = i['metadata']

    dictionary = open(dictionary_file,'w')
    postings = open(postings_file,'w')
    
    index = {'metadata':{}, 'content': {}, 'title': {}, 'docids':docids }
    
    print("Writing to files....")
    #add in meta data
    index = storein_metadata(postings,A_tags,index,'tags')
    index = storein_metadata(postings,A_areaoflaw,index,'areaoflaw')
#     index = storein_metadata(metadata,A_jury,index,'jur')
#     index = storein_metadata(metadata,A_court,index,'court')
    index['metadata'] = A_metadata
    
    index = store_content1(postings,A_content,index,'content')
  
    index = store_title1(postings,A_title,index,'title')
    
    
    json.dump(index,dictionary)
    dictionary.close()
    postings.close()
    print("Done!")


def usage():
    print ("usage: " + sys.argv[0] + " -i directory-of-documents -d dictionary-file -p postings-file")

directory_of_documents = dictionary_file = postings_file = None
try:
    opts, args = getopt.getopt(sys.argv[1:], 'i:d:p:')
except (getopt.GetoptError, err):
    usage()
    sys.exit(2)
for o, a in opts:
    if o == '-i':
        directory_of_documents = a
    elif o == '-d':
        dictionary_file = a
    elif o == '-p':
        postings_file = a
    else:
        assert False, "unhandled option"
if directory_of_documents == None or dictionary_file == None or postings_file == None:
    usage()
    sys.exit(2)

if __name__ == '__main__':
    start = time.time()
    b = make_dictionary1(directory_of_documents, dictionary_file, postings_file)
    end = time.time()
    print("Time taken: " + str(end-start))


