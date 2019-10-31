import random
from typing import List
from sortedcontainers import SortedSet

from wordplay import config


def load_docs(corpus_name: str,
              shuffle_docs: bool = False,
              num_test_take_from_mid: int = 0,
              num_test_take_random: int = 100,
              start_at_midpoint: bool = False,
              start_at_ends: bool = False,
              split_seed: int = 3,
              shuffle_seed: int = 20,  # 20 results in pretty even probe distribution
              ) -> List[str]:

    p = config.Dirs.corpora / f'{corpus_name}.txt'
    docs = p.read_text().split('\n')
    num_docs = len(docs)
    print(f'Loaded {num_docs} documents from {corpus_name}')

    assert not(shuffle_docs and start_at_midpoint and start_at_ends)
    assert not(shuffle_docs and start_at_midpoint)
    assert not(shuffle_docs and start_at_ends)
    assert not(start_at_midpoint and start_at_ends)

    # test doc ids
    midpoint = len(docs) // 2
    test_doc_ids = SortedSet(range(midpoint, midpoint + num_test_take_from_mid))  # from middle
    #
    num_random_ids = num_docs - num_test_take_random
    random.seed(split_seed)
    random_test_doc_ids = set(random.sample(range(num_random_ids), num_test_take_random))
    test_doc_ids.update(random_test_doc_ids)

    # split train/test
    if test_doc_ids:
        print(f'Removing {len(test_doc_ids)} test documents')
    train_docs = []
    for n, doc in enumerate(docs):
        if n not in test_doc_ids:
            train_docs.append(doc)

    if shuffle_docs:
        random.seed(shuffle_seed)
        print('Shuffling documents')
        random.shuffle(train_docs)

    if start_at_midpoint:
        train_docs = reorder_docs_from_midpoint(train_docs)

    if start_at_ends:
        train_docs = reorder_docs_from_ends(train_docs)

    return train_docs


def reorder_docs_from_midpoint(docs: List[str]
                               ) -> List[str]:
    """
    reorder docs such that first docs are docs that are most central
    """
    # start, middle, end
    s = 0
    e = len(docs)
    m = e // 2

    res = []
    for i, j in zip(range(m, e + 1)[::+1],
                    range(s, m + 0)[::-1]):
        res += [docs[i], docs[j]]

    assert len(res) == len(docs)

    return res


def reorder_docs_from_ends(docs: List[str]
                           ) -> List[str]:
    """
    reorder docs such that first docs are docs that are from ends
    """
    # start, middle, end
    s = 0
    e = len(docs)
    m = e // 2

    res = []
    for i, j in zip(range(m, e + 0)[::-1],
                    range(s, m + 1)[::+1]):
        res += [docs[i], docs[j]]

    assert len(res) == len(docs)

    return res
