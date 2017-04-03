import string
from nltk.stem.porter import PorterStemmer
import xml.etree.ElementTree as ET
import os
import json
import getopt
import sys
from util import tf,L2norm

stemmer = PorterStemmer()
def clean_content(text):
    
    chars = string.punctuation + '”' + '’' + '“' + '…'
    
    text = text.lower() #lowercase
    text = text.replace('\n', ' ') #remove newline characters
    text = text.replace('\t',' ') # trim whitespaces including tabs etc
    text = text.replace('\xa0', ' ') #remove \xa0 (non-breaking space in latin)
    text = [stemmer.stem(i).strip(chars) for i in text.split() if stemmer.stem(i).strip(chars)]
    
    return text


def stemmed_tags(tags):
    result = []
    for tag in tags:
        words = tag.text.split()
        words = [stemmer.stem(word.lower()) for word in words]
        
        result.append(' '.join(words))
        
    return result


def make_dictionary(directory,dictionary_file,postings_file):
    
    filenames = os.listdir(directory)
    if directory[-1]!='/':
        directory = directory+'/'
        
    docids = []
    A_tags = {}
    A_dateposted = {}
    A_content = {}
    A_title = {}
    A_jurisdiction = {}
    A_court = {}
    tfs = {}
    total_df = len(filenames)
    #print(total_df)
    
    for filename in filenames:
        tree = ET.parse(directory+filename)
        root = tree.getroot()
        d = {}
        for child in root:
            key = child.attrib.get('name')
            value = child
            d[key] = value
            
        docid = int(d['document_id'].text)
        
        #tags
        if 'tag' in d.keys():
            tags = stemmed_tags(d['tag'])#get a list of tags
            for tag in tags:
                if tag not in A_tags:
                    A_tags[tag] = [docid]

                else:
                    Atags[tag].append(docid)

        
        
        #dateposted
        if 'date_posted' in d.keys():
            date = d['date_posted'].text[:10] #get only the yyyy-mm-dd
            if date not in A_dateposted:
                A_dateposted[date] = [docid]
            else:
                A_dataposted[date].append(docid)
            
        
        
        #content (positional indexes)
        if 'content' in d.keys():
            content = clean_content(d['content'].text)
            contentsize = len(content)
            for index,term in enumerate(content):
                if term not in A_content: #new term, new docid
                    A_content[term] = {docid:[index]}

                else: # term exists
                    if docid not in A_content[term]: # if docid does not exists
                        A_content[term][docid] = [index]

                    else: #docid exists
                        A_content[term][docid].append(index)
            
            length = []
            for term in A_content:
                if docid in A_content[term]:
                    if term not in tfs:
                        tfs[term] = {}
                        tfreq = tf(len(A_content[term][docid])) #log term frequency
                        tfs[term][docid] = tfreq
                        length.append(tfreq)
                    else:
                        tfreq = tf(len(A_content[term][docid])) #log term frequency
                        tfs[term][docid] = tfreq
                        length.append(tfreq)

            for term in tfs:
                if docid in tfs[term]:
                    tfs[term][docid] = tfs[term][docid]/L2norm(length) #normalisation

                    
        
        #title (positional indexes)
        if 'title' in d.keys():
            title = clean_content(d['title'].text)
            for index,term in enumerate(title):
                if term not in A_title:
                    A_title[term] = {docid:[index]}

                else:
                    if docid not in A_title[term]:
                        A_title[term][docid] = [index]
                    else:
                        A_title[term][docid].append(index)
                    
        
        #jurisdiction
        if 'jurisdiction' in d.keys():
            jurisdiction = d['jurisdiction'][0].text
            if jurisdiction not in A_jurisdiction:
                A_jurisdiction[jurisdiction] = [docid]
            else:
                A_jurisdiction[jurisdiction].append(docid)

        
        #court
        if 'court' in d.keys():
            court = d['court'].text
            if court not in A_court:
                A_court[court] = [docid]
            else:
                A_court[court].append(docid)
                
            
    
    #idf
    idfs = {}
    
    for term in A_content:
        df = len(A_content[term])
        print(df)
        idfs[term] = idf(df,total_df)
    
    
    
    
    dictionary = open(dictionary_file,'w')
    postings = open(postings_file,'w')
    index = {}
    result = {'tags': A_tags, 'date_posted': A_dateposted, 'content': A_content, 'title': A_title, 'jur': A_jurisdiction, 'court': A_court}
    for key in result:

        if key == 'content' or key == 'title':
            for term,value in result[key].items():
                for docid,position in result[key][term].items():
                    if term not in index:
                        start = postings.tell()
                        posting = ','.join(map(str,result[key][term][docid]))
                        posting = 's'+ str(docid) + ',' + posting
                        postings.write(posting)
                        index[term] = {str(key): start, str(key)+'len': len(posting)}
                    else:
                        start = postings.tell()
                        posting = ','.join(map(str,result[key][term][docid]))
                        posting = str(docid) + ',' + posting    
                        postings.write(posting)
                        index[term][str(key)] = start
                        index[term][str(key)+'len'] = len(posting)
                        
        else:
            for term,docids in result[key].items():
                if term not in index:
                    start = postings.tell()
                    posting = ','.join(map(str,docids))
                    postings.write(posting)
                    index[term] = {str(key):start, str(key)+'len': len(posting)}
                else:
                    start = postings.tell()
                    posting = ','.join(map(str,docids))
                    postings.write(posting)
                    index[term][str(key)] = start
                    index[term][str(key)+'len'] = len(posting)
                    
    
    
    json.dump(index,dictionary)
    dictionary.close()
    postings.close()

    return idfs


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