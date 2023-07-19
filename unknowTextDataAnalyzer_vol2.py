# main.py

# pylint: disable=missing-function-docstring
# pylint: disable=missing-module-docstring

import sys
import string
from collections import Counter
import json

import spacy

EXPECTED_ARGUMENTS = 3
PUNCTUATION = '<>=”}{:'
MAX_CLASS_COUNT = 10

ONE_WORD_KEY = {
    'COMPANY': {'business', 'product'},
    'PERSON': {'address', 'email', 'name'}
}

nlp_en = spacy.load('en_core_web_sm')


def processDataFile(path_to_file: str):
    '''
    Function processDataFile parse input data file and determine simillarity
    Input: path to data file, path to result json file
    Output: dictionary consist of results (main class and sub class)
    '''

    one_word = []
    group_of_word = []
    combinatons = []

    one_word_ids = []
    one_digit_ids = []
    one_alnum_ids = []
    one_punctuation_ids = []
    group_of_word_ids = []
    group_of_digit_ids = []
    group_of_alnum_ids = []
    group_of_punctuation_ids = []
    combinatons_ids = []

    collected_classes = {}

    with open(path_to_file, 'r') as data_file:
        for data_line in data_file:
            doc_id, doc_text = data_line.split('\t')

            if doc_text:

                # prepare data for analyzer
                clean_text = doc_text.translate(str.maketrans(dict.fromkeys(PUNCTUATION, ' ')))
                filtered_data = [word.strip(string.punctuation) for word in clean_text.split() if word.strip(string.punctuation)]

                # analyzer global point of view
                alpha = []
                digit = []
                alnum = []
                punctuation = []
                for word in filtered_data:
                    # collect only 3 character strings
                    if len(word) > 2:
                        if word.isalpha():
                            alpha.append(word.lower())
                        elif word.isdigit():
                            digit.append(word)
                        elif word.isalnum():
                            alnum.append(word.lower())
                        else:
                            punctuation.append(word.lower())

                # Main Classes selection - base on global point of view (content format)
                if len(alpha) == 1 and not digit and not alnum and not punctuation:
                    one_word.append({'doc_id': doc_id, 'keywords': alpha[0]})
                    one_word_ids.append(doc_id)
                elif not alpha and len(digit) == 1 and not alnum and not punctuation:
                    one_digit_ids.append(doc_id)
                elif not alpha and not digit and len(alnum) == 1 and not punctuation:
                    one_alnum_ids.append(doc_id)
                elif not alpha and not digit and not alnum and len(punctuation) == 1:
                    one_punctuation_ids.append(doc_id)
                elif len(alpha) > 1 and not digit and not alnum and not punctuation:
                    group_of_word.append({'doc_id': doc_id, 'keywords': alpha})
                    group_of_word_ids.append(doc_id)
                elif not alpha and len(digit) > 1 and not alnum and not punctuation:
                    group_of_digit_ids.append(doc_id)
                elif not alpha and not digit and len(alnum) > 1 and not punctuation:
                    group_of_alnum_ids.append(doc_id)
                elif not alpha and not digit and not alnum and len(punctuation) > 1:
                    group_of_punctuation_ids.append(doc_id)
                else:
                    keywords = {'alpha': alpha, 'digit': digit, 'alnum': alnum, 'punctuation': punctuation}
                    combinatons.append({'doc_id': doc_id, 'keywords': keywords})
                    combinatons_ids.append(doc_id)

    # SubClasses selection - base on content recognition
    hit_one_word = {}

    # one word - bese on keyword dictionaries
    for class_name in ONE_WORD_KEY.keys():
        for one_word_doc in one_word:
            for term in ONE_WORD_KEY[class_name]:
                if term in one_word_doc['keywords']:
                    if class_name not in hit_one_word.keys():
                        hit_one_word[class_name] = [one_word_doc['doc_id']]
                    else:
                        hit_one_word[class_name].append(one_word_doc['doc_id'])

    # group of words - bese on statistic (word maps)
    line_data = []
    tokens_summary = Counter()

    # generate wordmaps
    for words in group_of_word:
        filtered_text = ' '.join(words['keywords'])

        processed_text_en = nlp_en(filtered_text)
        word_tokens = [token.lemma_ for token in processed_text_en if not token.is_stop]

        no_duplicity = set(word_tokens)
        token_count = Counter(no_duplicity)
        tokens_summary += token_count

        word_map_line = {
            'doc_id': words['doc_id'],
            'tokens': no_duplicity
        }
        line_data.append(word_map_line)

    for item in combinatons:
        if len(item['keywords']['alpha']) > 1:
            filtered_text = ' '.join(item['keywords']['alpha'])

            processed_text_en = nlp_en(filtered_text)
            word_tokens = [token.lemma_ for token in processed_text_en if not token.is_stop]

            no_duplicity = set(word_tokens)
            token_count = Counter(no_duplicity)
            tokens_summary += token_count

            word_map_line = {
                'doc_id': item['doc_id'],
                'tokens': no_duplicity
            }
            line_data.append(word_map_line)

    word_map = dict(tokens_summary.most_common(MAX_CLASS_COUNT))

    # generate and formate collected results
    collected_classes['Main_classes'] = {
        'one_word': len(one_word_ids),
        'one_digit': len(one_digit_ids),
        'one_alnum': len(one_alnum_ids),
        'one_punctuation': len(one_punctuation_ids),
        'group_of_word': len(group_of_word_ids),
        'group_of_digit': len(group_of_digit_ids),
        'group_of_alnum': len(group_of_alnum_ids),
        'group_of_punctuation': len(group_of_punctuation_ids),
        'combinatons': len(combinatons_ids)
    }

    collected_classes['Sub_classes_stat'] = {
        'word_map': word_map,
        'document_count': len(line_data)
    }

    sub_classes_group_words = []
    for key in word_map.keys():

        doc_ids = []
        for line in line_data:
            if key in line['tokens']:
                doc_ids.append(line['doc_id'])

        sub_class = {
            'class_name': '{}'.format(key.upper()),
            'doc_ids': doc_ids,
            'doc_count': len(doc_ids)
        }
        sub_classes_group_words.append(sub_class)

    collected_classes['Sub_classes'] = {
        'one_word': hit_one_word,
        'group_words': sub_classes_group_words
    }

    return collected_classes


if __name__ == '__main__':
    args_count = len(sys.argv)
    if args_count < EXPECTED_ARGUMENTS:
        print('Invalid number of arguments {}, expect {}: path to tsv file'.format((args_count - 1), (EXPECTED_ARGUMENTS - 1)))
    elif args_count == EXPECTED_ARGUMENTS:
        pathToFile = sys.argv[1]
        pathToResult = sys.argv[2]
        results = processDataFile(pathToFile)

        with open(pathToResult, 'w') as data_file:
            json.dump(results, data_file)
    else:
        print('Invalid number of arguments {}, expect {}: path to tsv file'.format((args_count - 1), (EXPECTED_ARGUMENTS - 1)))
