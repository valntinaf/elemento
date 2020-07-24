import sys
import elemento.elemento as el
from colorama import Fore, Style
import requests
import json
import re
from nltk.corpus import stopwords
import gensim.downloader as api
import sys
from gensim.models.word2vec import Word2Vec
import gensim

RATIO = 0.8

notion = el.Notion()
question = sys.argv[1].lower()
words = []
stopwords = stopwords.words('english')
splitted = re.split(r"\s+(?=[^()]*(?:\(|$))", question)
sentences_for_training = []

for word in splitted:
    word = word.translate({ord(i):None for i in '¿?()\x00'})
    if word not in stopwords:
        words.append(word)

print("Reading question...")
asker = el.Notion()
question = question.translate({ord(i):None for i in '\n\t\x00?\([(^)]+'})
asker.process_sentence(question.lower())
if not asker.idees:
    print("The question wasn't understood")
    sys.exit()

print("Looking for results...")
full_text = []
for word in words:
    result = requests.get('https://en.wikipedia.org/w/api.php?format=json&action=query&prop=extracts&exintro&explaintext&redirects=1&titles='+word).content.decode("utf-8")
    wiki_response = json.loads(result)
    if list(wiki_response["query"]["pages"].keys())[0] != "-1":
        wiki_content = list(wiki_response["query"]["pages"].values())[0]["extract"]
        text = wiki_content.translate({ord(i):None for i in '\n\t\x00'})
        text = re.sub(r" ?\([(^)]+\)", "", text)
        text = text.split('.')
        sentences_for_training.append([ sentence.split() for sentence in text])
        full_text.extend(text)
    else:
        print("No information found")
        sys.exit()

if full_text:
    print("Processing text...")
    notion.process_text(full_text)

questions = []
for idee in notion.idees:
    questions.extend(
        [{
            "idee": idee,
            "questions": el.generate_questions(idee)
         }]
    )

try:
    model = gensim.models.Word2Vec.load("/wiki_trained_model")
except:
    corpus = api.load('wiki-english-20171001')
    model = Word2Vec(corpus)
    model.save("wiki_trained_model")
model.train(sentences_for_training, word_count=1)
question_vector = el.resolve_dictionary_wv(asker.idees[0], model=model)
dict_question = asker.idees[0]
solutions = []
for idee in notion.idees:
    dict_idee = idee
    valid = True
    idee_vector = el.resolve_dictionary_wv(idee, model=model)

    score = 0
    for key in question_vector.keys():
        if key in idee_vector.keys():
            a, b = model.similar_by_vector(question_vector[key],topn=1)[0]
            c, d = model.similar_by_vector(idee_vector[key],topn=1)[0]
            distance = model.distance(a,c)
            if distance < RATIO:
                score += 1-RATIO

    if score > 0:
        solutions.append(
            (idee_vector,score)
        )

for solution, score in solutions:
    for key in solution.keys():
        if key not in question_vector.keys():
            print(model.similar_by_vector(solution[key], topn=3))
