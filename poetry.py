from twython import Twython
from datetime import datetime
import time
import re
import random
import json
import nltk
from itertools import *
import sys

pronunciations = nltk.corpus.cmudict.dict()

def pronunciation(word):
    if word[0] == "#":
        word = word[1:]
    return pronunciations[word.lower()][0]

def isAWord(word):
    try:
        pronunciation(word)
        return True
    except KeyError:
        return False

# ==============================================================================

hashtag = "#YOLO"

twitter_keys = json.loads(open('twitter_keys.json').read())
twyt = Twython(**twitter_keys)

twitter_stuff_rx = re.compile(r"RT |@\S+|(?:#\S+\s*)*$|http://\S+")
twitter_hash_noun_rx = re.compile(r"#\S+")

def fixTwitterStuff(text):
    out = twitter_stuff_rx.sub("", text)
    #out = twitter_hash_noun_rx.sub(lambda m: m.group(0) if isAWord(m.group(0)) else "", out)
    return out

npages_to_use = 15
texts = []
next_results = None
for page_num in range(npages_to_use):
    if next_results is None:
        response = twyt.search(q=hashtag, lang="en", count=100)
    else:
        response = twyt.get('https://api.twitter.com/1.1/search/tweets.json' + next_results)

    statuses = response['statuses']
    for status in statuses:
        texts.append(fixTwitterStuff(status['text']))

    try:
        next_results = response['search_metadata']['next_results']
    except KeyError:
        break

# ==============================================================================

def stripStresses(pron):
    out = pron[:]
    for i, w in enumerate(out):
        if isVowel(w):
            out[i] = w[:-1]
    return out

def isVowel(phenome):
    return phenome[-1].isdigit()

def lastSyllable(pron):
    for i in range(len(pron) - 1, -1, -1):
        if isVowel(pron[i]):
            return stripStresses(pron[i:])
    return []

boring_rhymes = [['night', 'tonight'],
                 ['day', 'birthday', 'today', 'yesterday']]

for i, rhymes in enumerate(boring_rhymes):
    pair = map(pronunciation, rhymes)
    pair = map(tuple, rhymes)
    boring_rhymes[i] = frozenset(rhymes)

def isBoringRhyme(pron1, pron2):
    s = frozenset([tuple(pron1), tuple(pron2)])
    return any(map(lambda r: s <= r, boring_rhymes))

def doPronunciationsRhyme(pron1, pron2):
    return (pron1 != pron2 and
            not isBoringRhyme(pron1, pron2) and
            stripStresses(lastSyllable(pron1)) == stripStresses(lastSyllable(pron2)))

def numberOfSyllablesInWord(word):
    return len(filter(isVowel, word))

def numberOfSyllablesInScentence(scen):
    return sum(map(numberOfSyllablesInWord, scen))

# ==============================================================================

word_rx = re.compile(r"[a-zA-Z]+")
lines = reduce(list.__add__, map(nltk.tokenize.sent_tokenize, texts), [])
random.shuffle(lines)

printable_lines = []
pronunciated_lines = []
for line in lines:
    tokenized = nltk.tokenize.word_tokenize(line)
    tokenized = filter(word_rx.match, tokenized)
    try:
        if len(tokenized) > 0:
            pronunciated_lines.append(map(pronunciation, tokenized))
            printable_lines.append(line.strip())
    except KeyError:
        pass

def find_lines(candidate_lines, line_indicies, rhyming_pattern, syllable_pattern):
    my_index = len(line_indicies)
    rhyming_line_index = rhyming_pattern.index(rhyming_pattern[my_index])
    rhyming_pron = candidate_lines[line_indicies[rhyming_line_index]][-1] if rhyming_line_index < my_index else None
    min_syls, max_syls = syllable_pattern[my_index]

    for i, line in enumerate(candidate_lines):
        already_used = False
        for j in line_indicies:
            if candidate_lines[i][-1] == candidate_lines[j][-1]:
                already_used = True
        rhymes = doPronunciationsRhyme(line[-1], rhyming_pron) if rhyming_pron is not None else True
        syls = numberOfSyllablesInScentence(line)
        matches_syls = min_syls <= syls <= max_syls

        if not (not already_used and rhymes and matches_syls):
            continue
        elif my_index == len(rhyming_pattern) - 1:
            return line_indicies + [i]
        else:
            attempt = find_lines(candidate_lines, line_indicies + [i], rhyming_pattern, syllable_pattern)
            if attempt:
                return attempt
    return False

def find_poem(rhyming_pattern, syllable_pattern, indents=None):
    line_indicies = find_lines(pronunciated_lines, [], rhyming_pattern, syllable_pattern)
    if line_indicies:
        out = map(lambda i: printable_lines[i], line_indicies)
        if indents:
            for i, l in enumerate(out):
                out[i] = indents[i] * " " + l
        return "/\n".join(out)

limerick_rhyming_pattern = "AABBA"
limerick_syllable_pattern = [[6, 8], [6, 8], [4, 5], [4, 5], [7, 8]]
limerick_indents = [0, 0, 2, 2, 0]

haiku_rhyming_pattern = "ABC"
haiku_syllable_pattern = [[5, 5], [7, 7], [5, 5]]

poem = find_poem(limerick_rhyming_pattern, limerick_syllable_pattern) + "\n" + hashtag

print poem
print

# ==============================================================================

if "--no-confirm" in sys.argv or raw_input("Publish? ") == "yes":
    twyt.updateStatus(status=poem)
