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


def make_dictionary(directory,dictionary_file,postings_file,metadata_file):
    
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
    #idf
    idfs = {}
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
        idfs[term] = idf(df,total_df)
    
    
    
    
    dictionary = open(dictionary_file,'w')
    postings = open(postings_file,'w')
    metadata = open(metadata_file,'w')
    
    index = {'metadata':{}, 'content': {}, 'title': {} }
    
    #add in meta data
    index = storein_metadata(metadata,A_tags,index,'tags')
    index = storein_metadata(metadata,A_dateposted,index,'date_posted')
    index = storein_metadata(metadata,A_jurisdiction,index,'jur')
    index = storein_metadata(metadata,A_court,index,'court')
    
    #add in content
    index = store_content(postings,A_content,index,'content',idfs)
    
    #add in title
    index = store_title(postings,A_title,index,'title')
    
    
    json.dump(index,dictionary)
    dictionary.close()
    postings.close()
    metadata.close()
    


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