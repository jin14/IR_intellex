import math


def tf(count):
	# calculate the logarithmic term frequency
    if count > 0:
        return 1 + math.log10(count)
    else:
        return 0


def idf(docfreq,totaldocs):
    # compute the inverse document frequency score
    return math.log10(totaldocs/docfreq)


def L2norm(k):
	# compute the L2 norm of the term
    return math.sqrt(sum(map(lambda x:x**2 if x>0 else 0,k)))  