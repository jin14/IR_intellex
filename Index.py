import string
from nltk.stem.porter import PorterStemmer
from nltk.tokenize import word_tokenize, sent_tokenize
import xml.etree.ElementTree as ET 
import os
import json
import getopt
import sys
import time
import math
import re
import multiprocessing
from multiprocessing import Pool

# global stemmer that is used for stemming
stemmer = PorterStemmer()

# This function is used to calculate the logarithmic term frequency
def tf(count):
# Returns 1 + log(raw term frequency) if the term is present else 0
    if count > 0:
        return 1 + math.log10(count)
    else:
        return 0

# This function is used to calculate the inverse document frequency of the term. It takes two params
# docfreq = number of documents in which the term appears
# totaldocs = total number of documents in the collection
def idf(docfreq,totaldocs):
#Returns the inverse document frequency of a term

    return math.log10(totaldocs/docfreq)

# This function is used to calculate the L2 norm. It takes in a list of logarithmic term frequency of the terms in a document
# i.e. [tf(term1), tf(term2), ...]
def L2norm(k):
#Returns the L2 norm of a document

    return math.sqrt(sum(map(lambda x:x**2 if x>0 else 0,k)))

# This function is used to write the metadata to the postings file and store the starting byte of the postings file in the dictionary file
# It takes in four parameters:
# postings_file: the postings file name
# the data to be written to the postings file
# index = the dictionary that will be stored in the dictionary file
# key= the name of the data stored, e.g. tag, areaoflaw etc
def storein_metadata(postings_file,metadata,index,key):
#Returns a dictionary with the relevant starting byte of the metadata in the postings file


    index[key] = {} #instantiate an empty dictionary for the name of data (i.e. tag, areaoflaw etc)
    

    for term in metadata:
        start = postings_file.tell() # get the starting byte of the relevant file
        postings = ','.join(map(str,metadata[term])) + '\n' # Convert data to type string. Each line in the postigns file belong one term
        postings_file.write(postings) # write to file
        index[key][term] ={'start': start} #store the starting byte of the data in the dictionary

    return index


# This function is specifically used to store the content section of the documents in the postings file.
# It takes in four parameters:
# posting_file = name of postings file
# content = content to be written to the postings file
# index = the dictionary to store the starting byte of the data
# key = the name of the data which is 'content' in this case
def store_content1(posting_file,content,index,key):
    
    for term in content:
        
        start = posting_file.tell() # get starting byte of the postings file
        postings = str(content[term]) + '\n' # convert to type string
        posting_file.write(postings) # write to postings file
    
        index[key][term] = {'s': start} # store the starting byte

    return index

# This function is specifically used to store the title section of the documents in the postings file.
# It takes in four parameters:
# posting_file = name of postings file
# title = title to be written to the postings file
# index = the dictionary to store the starting byte of the data
# key = the name of the data which is 'title' in this case
def store_title1(posting_file,title,index,key):
    
    for term in title:
        
        start = posting_file.tell() # get starting byte of the postings file
        postings = str(title[term]) + '\n' # convert to string
        posting_file.write(postings) # write to postigns file      
        index[key][term] = {'s':start} # store the starting byte of the file in dictionary
    return index


# This function is specifically used to extract all the sections of the documents that we deem relevant.
# It takes in one parameter: 
# path: filepath of the document
def extract_info1(path):
#Returns a dictionary with the tag,content,title,areaoflaw,dateposted,court,jury data of a document

    print(path) # we print the filepath as a sign to know that the code is running
    A_tags = {} # dictonary to store all the <tags> data
    A_content = {} # dictonary to store all the <content> data
    A_title = {} # dictonary to store all the <title> data
    tfs = {} # dictonary to store all the tfs of the terms in a document
    A_areaoflaw = {} # dictonary to store all the <areaoflaw> data
    
    tree = ET.parse(path) # parse the xml document into an elementTree
    
    docid = int(tree.find(".//str[@name='document_id']").text) # find the document id
    date_posted = tree.find(".//date[@name='date_posted']").text[:10] # find the date
    title = tree.find(".//str[@name='title']").text # get the title
    content = tree.find(".//str[@name='content']").text # get the content
    
    court = [i.text for i in tree.findall(".//str[@name='court']")] # get the court
    jury = [i.text for i in tree.findall(".//arr[@name='jurisdiction']/str")] # get the jurisdiction
    tag = [i.text for i in tree.findall(".//arr[@name='tag']/str")] # get the tags
    areaoflaw = [i.text for i in tree.findall(".//arr[@name='areaoflaw']/str")] # get the areaoflaw

    
    A_areaoflaw = addtodict(areaoflaw,docid) # store the area of law data
    A_tags = addtodict(tag,docid) #store the tags data
    
    #metadata
    A_metadata = {'jury':jury, 'court': court, 'date_posted': date_posted } # store the jury, court and date_posted data
    
    #content
    content = clean_content(content) # do basic cleaning and stemming of the content
    contentsize = len(content) # get the length of the content 
    
    for index,term in enumerate(content):
        if term not in A_content:
            A_content[term] = {docid:{'index':[index], 'tf':None}} # store the positional index and instantiate empty term frequency value
        
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
                tfreq = tf(len(A_content[term][docid]['index'])) # calculate the logarithmic term frequency
                tfs[term][docid] = tfreq # store the termfrequency in the tf dictionary
                length.append(tfreq) # append the tf value of the term
            
            else:
                tfreq = tf(len(A_content[term][docid]['index'])) # calculate the logarithmic term frequency
                tfs[term][docid] = tfreq
                length.append(tfreq)
                
    
    norm = L2norm(length) # calculate the L2norm of the document
    for term in tfs:
        if docid in tfs[term]:
            tfs[term][docid] = tfs[term][docid]/norm # L2 normalisation of the document
            
    
    for term in A_content:
        if docid in A_content[term]:
            A_content[term][docid]['tf'] = tfs[term][docid] # replace all the empty tf values with normalised tf values in the dictionary
            
    
    #title
    for index,term in enumerate(title): 
        if term not in A_title:
            A_title[term] = {docid:[index]} # store the positional index of the terms in the title
        
        else:
            if docid not in A_title[term]:
                A_title[term][docid] = [index]
            else:
                A_title[term][docid].append(index)
                
    
    
    # store all the data in a overall dictionary
    A_overall = {'content':A_content, 'title': A_title, 'metadata': A_metadata ,'docid':docid, 'tags': A_tags, 'areaoflaw': A_areaoflaw}
    
     
    
    
    return A_overall

# This function is used to clean the text
# It takes in one param: text = the string of text to be cleaned 
def clean_content(text):
#Returns a list of cleaned terns

    chars = string.punctuation + '”' + '’' + '“' + '…' # punctuations to be removed
    
    text = text.lower() #lowercase

    text = re.sub('[^A-Za-z0-9]+', ' ', text)  #only keep the numbers and alphabets
    

    result = [sent for sent in sent_tokenize(text)] # sentence tokenisation 
    result = [word for sublist in result for word in word_tokenize(sublist)] # word tokenisation


    result = list(map(wordify,result)) # mao the wordify function to the list of words
    


    return result

# This function is used to stem the tags data
#  It takes in a list of tags
def stemmed_tags(tags):
#Returns a list of cleaned tags

    result = []
    for tag in tags:
        words = tag.split() # split by space
        words = [stemmer.stem(word.lower()) for word in words] # stem and lowercase the tags
        
        result.append(' '.join(words))
        
    return result


# This function is used to add the data to a dictionary
# It takes in two parameters:
# texts = data to be stored
# docid = document id of the data
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

# This function is used to merger the two dicionaries together. Primarily used to merge the content and title data because of they have positional indexes
def merge_CT(A,B):
    
    for term in B: 
        if term in A:
            A[term].update(B[term])
        else:
            A[term] = B[term]
            
    return A

# This function is used to merge two dictonaries of data together  
def mergerest(A,B):
    
    for term in B:
        if term in A:
            A[term].append(B[term])
        else:
            A[term] = B[term]
    
    return A

# This function is used to merge the tags data together
def mergerest_tags(A,B):
    
    for term in B:
        if term in A:
            A[term].extend(B[term])
        else:
            A[term] = B[term]
    
    return A

# This function is used to clean a word
def wordify(word):
    chars = string.punctuation + '”' + '’' + '“' + '…'
    
    try:
        word = stemmer.stem(word).strip(chars) # stem and remove unrelevant characters
    except:
        pass

    return word.strip(chars)

# This is the main function that does the entire indexing. It takes in three parameters
# directory = direfctory of the files
# dcionary_file = name of dictonary file
# postings_file = name of postings file 

def make_dictionary(directory,dictionary_file,postings_file):
#It does not return anything but it creates a dictionary file and postings file

    if directory[-1]!='/': # check if theres a trailing slash in the directory
        directory = directory+'/' 
        
    docids = [] # list of document ids
    A_tags = {} # dictionary of tags
    A_dateposted = {} # dictionary of dates
    A_content = {} # dictionary of content
    A_title = {} # dictionary of title
    A_jury = {} # dictionary of jury
    A_court = {} # dictionary of court
    tfs = {} # dictionary of tf values
    A_areaoflaw = {} # dictionary of area of law

    print("Scanning...")
    with os.scandir(directory) as theFiles:
        new = []
        for filename in theFiles:
            new.append(directory+filename.name)
            docids.append(filename.name[:-4]) # get all the docids of the file
            
    print("Extracting...")
    # just pool
    # pool = Pool()
    # result = pool.map(extract_info1, new)
    #pool = MyPool()

    # with cpu counts
    num_workers = multiprocessing.cpu_count() # get the cpu counts
    pool = multiprocessing.Pool(num_workers) # use pooling to make the entire process faster
    chunksize = len(new)//(4*num_workers) + 1
    result = pool.imap(extract_info1,new,chunksize) # apply the extract information method to all the 
    
    pool.close()

    
    print("Merging...")
    A_metadata = {}
    for i in result:
        A_content = merge_CT(A_content,i['content']) # merge the content results into a unified content dictionary
        A_title = merge_CT(A_title,i['title']) # merge the title results into a unified title dictionary
        A_areaoflaw = mergerest_tags(A_areaoflaw, i['areaoflaw']) # merge the areaoflaw results into a unified areaoflaw dictionary
        A_tags = mergerest_tags(A_tags,i['tags']) # merge the tags results into a unified tags dictionary
    
        A_metadata[i['docid']] = i['metadata'] # merge the metadata results into a unified metadata dictionary

    dictionary = open(dictionary_file,'w') 
    postings = open(postings_file,'w')
    
    index = {'metadata':{}, 'content': {}, 'title': {}, 'docids':docids }
    
    print("Writing to files....")
    #add in tags and areaoflaw data into the postings file
    index = storein_metadata(postings,A_tags,index,'tags') #
    index = storein_metadata(postings,A_areaoflaw,index,'areaoflaw')

    index['metadata'] = A_metadata
    
    # write content data to postings file
    index = store_content1(postings,A_content,index,'content')
  	
  	# write title data to postings file
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
except getopt.GetoptError as err:
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
    b = make_dictionary(directory_of_documents, dictionary_file, postings_file)
    end = time.time()
    print("Time taken: " + str(end-start))


