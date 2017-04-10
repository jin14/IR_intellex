import string
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem.porter import PorterStemmer
#import xml.etree.ElementTree as ET 127.96343898773193
from lxml import etree as ET
#import xml.etree.cElementTree as ET
import os
import json
import getopt
import sys
from util import tf,L2norm,idf
import time
import re

stemmer = PorterStemmer()
def clean_content(text):
    
    chars = string.punctuation + '”' + '’' + '“' + '…'
    
    text = text.lower() #lowercase
    # text = text.replace('\n', ' ') #remove newline characters
    # text = text.replace('\t',' ') # trim whitespaces including tabs etc
    # text = text.replace('\xa0', ' ') #remove \xa0 (non-breaking space in latin)
    # text = text.replace(r'\u20', ' ')
    text = re.sub('[^A-Za-z0-9]+', ' ', text) # only keep alphabets and numbers, removes the rest

    result = []

    for sentence in sent_tokenize(text):
    	for word in word_tokenize(sentence):
    		try:
    			if stemmer.stem(word).strip(chars):
    				result.append(stemmer.stem(word).strip(chars))
    		except:
    			result.append(i)		
		
    # for i in text.split():
    #     try:
    #         if stemmer.stem(i).strip(chars):
    #             result.append(stemmer.stem(i).strip(chars))
    #     except:
    #         result.append(i)
           
	
    return result


def stemmed_tags(tags):
    result = []
    for tag in tags:
        words = tag.text.split()
        words = [stemmer.stem(word.lower()) for word in words]
        
        result.append(' '.join(words))
        
    return result


def storein_metadata(metadata_file,metadata,index,key):
    
    index['metadata'][key] = {}
    
    for term in metadata:
        start = metadata_file.tell()
        postings = ','.join(map(str,metadata[term]))
        metadata_file.write(postings)
        index['metadata'][key][term] ={'start': start, 'len': len(postings)}

    return index


def store_content(posting_file,content,index,key,idfs):
    
    for term in content:
        index[key][term] = {'idf': idfs[term]}
        for docid in content[term]:
            start = posting_file.tell()
            postings = ','.join(map(str,content[term][docid]['index']))
            posting_file.write(postings)
            index[key][term][docid] = {'start':start, 'len':len(postings), 'tf': content[term][docid]['tf']}
    
    return index

def store_title(posting_file,title,index,key):
    
    for term in title:
        index[key][term] = {}
        for docid in title[term]:  
            start = posting_file.tell()
            postings = ','.join(map(str,title[term][docid]))
            posting_file.write(postings)
            index[key][term][docid] = {'start': start, 'len':len(postings)}
            
    
    return index
    
def stemmed_tags_new(tags,d,docid):
    for tag in tags:
        words = tag.split()
        words = [stemmer.stem(word.lower()) for word in words]
        newtag = ' '.join(words)
        if newtag:
            if newtag not in d:
                d[newtag] = [docid]
            else:
                d[newtag].append(docid)
        
    return d


def make_dictionary1(directory,dictionary_file,postings_file,metadata_file):
    
    filenames = os.listdir(directory)
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
    #idf
    idfs = {}
    total_df = len(filenames)
    #print(total_df)
    
    with os.scandir(directory) as theFiles:

        for filename in theFiles:
            print(filename.name)
            tree = ET.iterparse(directory+filename.name)
            
            for event,elem in tree:
                if 'name' in elem.attrib:
                    if elem.attrib['name'] == 'document_id':
                        docid = int(elem.text)
                        docids.append(docid)
                    
                    elif elem.attrib['name'] == 'tag':
                        A_tags = stemmed_tags_new(elem.itertext(),A_tags,docid)
                        elem.clear()
                        
                    elif elem.attrib['name'] == 'date_posted':
                        date = elem.text[:10]
                        if date not in A_dateposted:
                            A_dateposted[date] = [docid]
                        else:
                            A_dateposted[date].append(docid)
                        
                        elem.clear()
                        
                    
                    elif elem.attrib['name'] == 'jurisdiction':
                        for jury in elem.itertext():
                            jury = jury.split()
                            if jury:
                                jury = jury[0]
                                if jury not in A_jury:
                                    A_jury[jury] = [docid]
                                else:
                                    A_jury[jury].append(docid)
                                    
                    elif elem.attrib['name'] == 'court':
                        for court in elem.itertext():
                            court = court.split()
                            if court:
                                court = court[0]
                                if court not in A_court:
                                    A_court[court] = [docid]
                                else:
                                    A_court[court].append(docid)
                        
                        elem.clear()
                    
                    elif elem.attrib['name'] == 'content':
                        content = clean_content(elem.text)
                        contentsize = len(content)
                        for index,term in enumerate(content):
                            if term not in A_content: #new term, new docid
                                A_content[term] = {docid:{'index':[index],'tf':None}}

                            else: # term exists
                                if docid not in A_content[term]: # if docid does not exists
                                    A_content[term][docid] = {'index':[index], 'tf':None}

                                else: #docid exists
                                    A_content[term][docid]['index'].append(index)

                        length = []
                        for term in A_content:
                            if docid in A_content[term]:
                                if term not in tfs:
                                    tfs[term] = {}
                                    tfreq = tf(len(A_content[term][docid]['index'])) #log term frequency
                                    tfs[term][docid] = tfreq
                                    length.append(tfreq)
                                else:
                                    tfreq = tf(len(A_content[term][docid]['index'])) #log term frequency
                                    tfs[term][docid] = tfreq
                                    length.append(tfreq)

                        for term in tfs:
                            if docid in tfs[term]:
                                tfs[term][docid] = tfs[term][docid]/L2norm(length) #normalisation


                        for term in A_content:
                            if docid in A_content[term]:
                                A_content[term][docid]['tf'] = tfs[term][docid]
                                    
                                
                    elif elem.attrib['name'] == 'title':
                        title = clean_content(elem.text)
                        for index,term in enumerate(title):
                            if term not in A_title:
                                A_title[term] = {docid:[index]}

                            else:
                                if docid not in A_title[term]:
                                    A_title[term][docid] = [index]
                                else:
                                    A_title[term][docid].append(index)

 
    #idf
    idfs = {}
    
    for term in A_content:
        df = len(A_content[term])
        idfs[term] = idf(df,total_df)
    
    
    
    
    dictionary = open(dictionary_file,'w')
    postings = open(postings_file,'w')
    metadata = open(metadata_file,'w')
    
    index = {'metadata':{}, 'content': {}, 'title': {}, 'docids':docids }
    
    #add in meta data
    index = storein_metadata(metadata,A_tags,index,'tags')
    index = storein_metadata(metadata,A_dateposted,index,'date_posted')
    index = storein_metadata(metadata,A_jury,index,'jur')
    index = storein_metadata(metadata,A_court,index,'court')
    
    #add in content
    index = store_content(postings,A_content,index,'content',idfs)
    
    #add in title
    index = store_title(postings,A_title,index,'title')
    
    
    json.dump(index,dictionary)
    dictionary.close()
    postings.close()

def usage():
    print ("usage: " + sys.argv[0] + " -i directory-of-documents -d dictionary-file -p postings-file -m metadata_file")

directory_of_documents = dictionary_file = postings_file = metadata_file = None
try:
    opts, args = getopt.getopt(sys.argv[1:], 'i:d:p:m:')
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
    elif o == '-m':
        metadata_file = a
    else:
        assert False, "unhandled option"
if directory_of_documents == None or dictionary_file == None or postings_file == None or metadata_file == None:
    usage()
    sys.exit(2)


start = time.time()
print("Creating index...")
make_dictionary1(directory_of_documents,dictionary_file,postings_file,metadata_file)
end = time.time()
print("Time taken to index: " + str(end-start))


