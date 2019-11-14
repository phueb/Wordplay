"""
Research questions:
1. How well does does semantic and syntactic complexity predict noun-context selectivity controlling for MLU?
2. Is the effect of MLU on noun-context-selectivity mediated via semantic or syntactic complexity or both?

A caveat:
The context-selectivity measure is extremely sensitive to the number of tokens.
This means that comparing selectivity at age bins,
 care must be taken to sample an equal number of words at each bin.
In fact, this script partitions the corpus without considering that partitions neatly fit into a single age

"""
import matplotlib.pyplot as plt
import spacy
import numpy as np
import attr
import pingouin as pg
from pingouin import mediation_analysis
from sklearn.preprocessing import StandardScaler
import pandas as pd

from preppy.legacy import TrainPrep
from categoryeval.probestore import ProbeStore

from wordplay.regression import regress
from wordplay.load import load_docs
from wordplay.params import PrepParams
from wordplay.utils import split
from wordplay.representation import make_context_by_term_matrix
from wordplay.measures import calc_selectivity
from wordplay.measures import calc_utterance_lengths
from wordplay.sentences import split_into_sentences
from wordplay.svo import subject_verb_object_triples

# /////////////////////////////////////////////////////////////////

CORPUS_NAME = 'childes-20180319'
PROBES_NAME = 'syn-4096'

REVERSE = False
NUM_PARTS = 64  # approx. 30-50
SHUFFLE_DOCS = False
SHUFFLE_SENTENCES = False  # this is the only way to completely remove age-structure (also within documents)

docs1 = load_docs(CORPUS_NAME,
                  num_test_take_from_mid=0,
                  num_test_take_random=0,
                  shuffle_sentences=SHUFFLE_SENTENCES,
                  shuffle_docs=SHUFFLE_DOCS)

params1 = PrepParams(num_parts=NUM_PARTS, reverse=REVERSE)
prep1 = TrainPrep(docs1, **attr.asdict(params1))

docs2 = load_docs(CORPUS_NAME + '_tags',
                  num_test_take_from_mid=0,
                  num_test_take_random=0,
                  shuffle_sentences=SHUFFLE_SENTENCES,
                  shuffle_docs=SHUFFLE_DOCS)

params2 = PrepParams(num_parts=NUM_PARTS, reverse=REVERSE)
prep2 = TrainPrep(docs2, **attr.asdict(params2))

probe_store = ProbeStore('childes-20180319', PROBES_NAME, prep1.store.w2id)

# ///////////////////////////////////////////////////////////////// parameters

CONTEXT_SIZE = 3
POS = 'NOUN'
ADD_SEM_PROBES = True  # set to True

# names
MLU = 'MLU'
SEM_COMPLEXITY = 'sem-complexity'
SYN_COMPLEXITY = 'syn-complexity'
SELECTIVITY = f'{POS}-context-selectivity'

# /////////////////////////////////////////////////////////////////

pos_words = probe_store.cat2probes[POS].copy()

if ADD_SEM_PROBES:
    added_probes = ProbeStore('childes-20180319', 'sem-all', prep1.store.w2id).types.copy()
    pos_words.update(added_probes)

# get a subset of pos_words which occur in ALL parts of corpus
for tokens in split(prep1.store.tokens, prep1.num_tokens_in_part):
    types_in_part = set(tokens)
    pos_words.intersection_update(types_in_part)
print(f'Number of {POS} words that occur in all partitions = {len(pos_words)}')

nlp = spacy.load("en_core_web_sm", disable=['ner'])

mlu = []
syn_complexity = []
sem_complexity = []
selectivity = []
for word_tokens, tag_tokens in zip(split(prep1.store.tokens, prep1.num_tokens_in_part),
                                   split(prep2.store.tokens, prep2.num_tokens_in_part)):

    assert len(word_tokens) == len(tag_tokens)
    assert word_tokens != tag_tokens

    # check
    num_pos_words_at_bin = len([w for w in pos_words if w in word_tokens])
    print(f'Using {num_pos_words_at_bin} probes to compute selectivity')

    # /////////////////////////////////// calc MLU

    lengths = calc_utterance_lengths(word_tokens)
    mlu_i = np.mean(lengths)

    # /////////////////////////////////// calc syntactic complexity

    tag_sentences = split_into_sentences(tag_tokens, punctuation={'.', '!', '?'})
    unique_sentences = np.unique(tag_sentences)
    syn_complexity_i = len(unique_sentences) / len(tag_sentences)

    # /////////////////////////////////// calc semantic complexity

    # compute num SVO triples as measure of semantic complexity
    word_sentences = split_into_sentences(word_tokens, punctuation={'.', '!', '?'})
    texts = [' '.join(s) for s in word_sentences]
    unique_triples = set()
    for doc in nlp.pipe(texts):
        for t in subject_verb_object_triples(doc):  # only returns triples, not partial triples
            unique_triples.add(t)
    num_unique_triples_in_part = len(unique_triples)
    sem_complexity_i = num_unique_triples_in_part

    # /////////////////////////////////// calc selectivity

    # co-occurrence matrix
    tw_mat_observed, xws_observed, _ = make_context_by_term_matrix(word_tokens,
                                                                   context_size=CONTEXT_SIZE,
                                                                   shuffle_tokens=False)
    tw_mat_chance, xws_chance, _ = make_context_by_term_matrix(word_tokens,
                                                               context_size=CONTEXT_SIZE,
                                                               shuffle_tokens=True)

    # calc selectivity of noun contexts
    cttr_chance, cttr_observed, selectivity_i = calc_selectivity(tw_mat_chance,
                                                                 tw_mat_observed,
                                                                 xws_chance,
                                                                 xws_observed,
                                                                 pos_words)

    print(f'selectivity={selectivity_i}\n'
          f'mlu={mlu_i}\n'
          f'syn-complexity={syn_complexity_i}\n'
          f'sem-complexity={sem_complexity_i}\n')
    print()

    # collect
    selectivity.append(selectivity_i)
    mlu.append(mlu_i)
    syn_complexity.append(syn_complexity_i)
    sem_complexity.append(sem_complexity_i)

# regress selectivity on mlu + sem-complexity
x = pd.DataFrame(data={MLU: mlu, SEM_COMPLEXITY: sem_complexity})
x[x.columns] = StandardScaler().fit_transform(x)
y = pd.Series(selectivity)
y.name = SELECTIVITY
summary = regress(x, y)  # reduces same results as sklearn with intercept + normalization
print(summary)

# regress selectivity on mlu + syn-complexity
x = pd.DataFrame(data={MLU: mlu, SEM_COMPLEXITY: sem_complexity})
x['mlu*sen-comp'] = x[MLU] * x[SEM_COMPLEXITY]  # TODO Test the interaction
x[x.columns] = StandardScaler().fit_transform(x)
y = pd.Series(selectivity)
y.name = SELECTIVITY
summary = regress(x, y)  # reduces same results as sklearn with intercept + normalization
print(summary)

# regress selectivity on mlu + syn-complexity
x = pd.DataFrame(data={MLU: mlu, SYN_COMPLEXITY: syn_complexity})
x[x.columns] = StandardScaler().fit_transform(x)
y = pd.Series(selectivity)
y.name = SELECTIVITY
summary = regress(x, y)  # reduces same results as sklearn with intercept + normalization
print(summary)

# regress selectivity on mlu + syn-complexity
x = pd.DataFrame(data={MLU: mlu, SYN_COMPLEXITY: syn_complexity})
x['mlu*syn-comp'] = x[MLU] * x[SYN_COMPLEXITY]  # TODO Test the interaction
x[x.columns] = StandardScaler().fit_transform(x)
y = pd.Series(selectivity)
y.name = SELECTIVITY
summary = regress(x, y)  # reduces same results as sklearn with intercept + normalization
print(summary)

# correlation matrix
x_all = pd.DataFrame(data={MLU: mlu, SYN_COMPLEXITY: syn_complexity, SEM_COMPLEXITY: sem_complexity})
x_all[x_all.columns] = StandardScaler().fit_transform(x_all)
correlations = x_all.corr()
print(correlations.round(3))

# scatter
xy = pd.concat((x_all, y), axis=1)
_, ax1 = plt.subplots()
xy.plot(kind='scatter', x=SEM_COMPLEXITY, y=SELECTIVITY, ax=ax1)  # nonlinear effect
plt.show()
_, ax2 = plt.subplots()
xy.plot(kind='scatter', x=SYN_COMPLEXITY, y=SELECTIVITY, ax=ax2)  # nonlinear effect
plt.show()
_, ax3 = plt.subplots()
xy.plot(kind='scatter', x=MLU, y=SELECTIVITY, ax=ax3)  # nonlinear effect
plt.show()

# partial correlation (controlling for mlu)
res1 = pg.partial_corr(data=xy, x=SEM_COMPLEXITY, y=SELECTIVITY, covar=MLU)
print('Partial Correlation between sem-comp and selectivity controlling for mlu')
print(res1)
res2 = pg.partial_corr(data=xy, x=SYN_COMPLEXITY, y=SELECTIVITY, covar=MLU)
print('Partial Correlation between syn-comp and selectivity controlling for mlu')
print(res2)

# mediation analysis
res = mediation_analysis(data=xy, x=MLU, m=[SYN_COMPLEXITY, SEM_COMPLEXITY], y=SELECTIVITY)
print(res)