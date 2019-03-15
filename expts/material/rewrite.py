# Copyright 2018 Johns Hopkins University. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific lang governing permissions and
# limitations under the License.
# =============================================================================

"""Convert DOMAIN.tsv file to format to submit to the server

Note: this is the new version for the new evaluation plan

input: directory path that contains 1A.txt and 1B.txt
submission files would be written into input/1A and input/1B

1A.txt and 1B.txt should contain path to find the predictions(composed of DOMAIN_datasetsuffix_min_..._max_..._vocab_..._tok_...architecture) and positive cut (in range (0.0, 1.0)) for each domain, e.g.:
GOV GOV_turk_60_50_min_1_max_-1_vocab_-1_doc_-1_tok_tweet_dan_meanmax_relu_0.1_nopretrain 0.5
"""
import math
import os
import shutil
import sys
import tarfile
from pprint import pprint

from material_constants import *

from expts.material.material_constants import LANG_DIRS, ERROR_FILES
from mtl.util.util import make_dir

text_type = 'doc'  # TODO


# translation = 'one'  # TODO


def main():
    pred_filenames = {
        '1A': {},
        '1B': {},
        '1S': {}
    }
    # TODO
    thresholds = {
        '1A': {},
        '1B': {},
        '1S': {}
    }
    sorted_scores = {
        '1A': {},
        '1B': {},
        '1S': {}
    }
    submission_dir = sys.argv[1]
    eval_dir = sys.argv[2]  # DEV
    translation = sys.argv[3]  # one / bop
    if len(sys.argv) == 5:
        T = float(sys.argv[4])
    else:
        T = 1

    exist = True

    for lang in LANG_DIRS:
        if not lang == '1S':
            continue
        filename = os.path.join(submission_dir, lang + '.txt')
        if not os.path.exists(filename):
            continue
        print(filename)
        with open(filename) as file:
            for line in file.readlines():
                if not line.strip():
                    continue
                line = line.split()
                # print(line)
                domain = line[0]
                encoder = line[1]
                threshold = float(line[2])
                # print(domain, threshold)
                dir_name = eval_dir
                dirs = DIRS[translation]
                for basedir, subdirs in dirs.items():
                    if lang not in basedir:
                        continue
                    basedir = os.path.join(text_type, basedir, dir_name)
                    for subdir in subdirs:
                        pred_filename = os.path.join(
                            'data/predictions', basedir, subdir, encoder,
                            domain + '.tsv')
                        # print(pred_filename)
                        if not os.path.exists(pred_filename):
                            print(pred_filename, 'doesnt exist!')
                            exist = False
                            continue
                        if domain not in pred_filenames[lang]:
                            pred_filenames[lang][domain] = []
                        pred_filenames[lang][domain].append(
                            pred_filename)
                if domain not in thresholds[lang]:
                    thresholds[lang][domain] = []
                thresholds[lang][domain] = threshold

    if not exist:
        print('Some files do not exist. Exiting...')
        exit()

    # pprint(pred_filenames)
    pprint(thresholds)

    for lang, domains in LANG_DIRS.items():
        if not lang == '1S':
            continue
        dout = os.path.join(submission_dir, eval_dir, translation, lang)
        if T != 1:
            dout += '_' + str(T)
        if os.path.exists(dout):
            shutil.rmtree(dout)
        make_dir(dout)
        print(dout)

        for domain in domains:
            threshold = thresholds[lang][domain]

            # keep track of all the scores
            scores = []

            with open(os.path.join(dout, domain + '.tsv'), 'a') as fout:
                # fout.write(DOMAIN_NAMES[domain][2:-4] + '\n')
                for filename in pred_filenames[lang][domain]:
                    with open(filename) as fin:
                        num_pos = 1
                        for line in fin.readlines()[1:]:
                            line = line.split()
                            id = line[0]
                            # remove error filenames
                            if id in ERROR_FILES[eval_dir]:
                                continue
                            label = line[1]
                            score = float(line[2])
                            scores.append(score)

                            # if int(label) == 1:
                            #   fout.write(id + '\t' + score + '\n')
                            # assert int(label) == 1 and float(score) >= 0.5 or int(
                            #   label) == 0 and \
                            #        float(score) < 0.5

                            # rescale
                            score = add_temperature(score, T)

                            if score > threshold:  # TODO
                                num_pos += 1
                                fout.write(id + '\tY\t' +
                                           format(score, '.5f') + '\n')
                            else:
                                fout.write(id + '\tN\t' +
                                           format(score, '.5f') + '\n')

            print(lang, domain, num_pos)

            scores.sort(reverse=True)

            sorted_scores[lang][domain] = scores

    # # TODO rewrite the max fixed length version
    # for lang, domains in LANG_DIRS.items():
    #   if not lang == '1S':
    #     continue
    #   dout = os.path.join(submission_dir, eval_dir, translation, lang)
    #   if T != 1:
    #     dout += '_' + str(T)
    #   if os.path.exists(dout):
    #     shutil.rmtree(dout)
    #   make_dir(dout)
    #   print(dout)
    #
    #   for domain in domains:
    #     # import pdb;pdb.set_trace()
    #     cut = thresholds[lang][domain]
    #     if cut < 1:
    #       continue
    #
    #     print('Rewriting!')
    #
    #     old_num = DEV_POS_NUM[lang][domain]
    #     old_threshold = sorted_scores[lang][domain][old_num]
    #     num = int(cut * old_num)
    #     threshold = sorted_scores[lang][domain][num]
    #     print(lang, domain, cut, old_num, num, old_threshold, threshold)
    #     fout = open(os.path.join(dout, domain + '.tsv'), 'a')
    #     # fout.write(DOMAIN_NAMES[domain][2:-4] + '\n')
    #     for filename in pred_filenames[lang][domain]:
    #       with open(filename) as fin:
    #         for line in fin.readlines()[1:]:
    #           line = line.split()
    #           id = line[0]
    #           # remove error filenames
    #           if id in ERROR_FILES[eval_dir]:
    #             continue
    #           label = line[1]
    #           score = float(line[2])
    #
    #           if score > threshold:  # TODO
    #             fout.write(id + '\tY\t' + format(score, '.5f') + '\n')
    #           else:
    #             fout.write(id + '\tN\t' + format(score, '.5f') + '\n')
    #
    #     fout.close()

    if eval_dir != 'DEV':
        return
    for lang, domains in LANG_DIRS.items():
        if not lang == '1S':
            continue

        dout = os.path.join(submission_dir, eval_dir, translation, lang)
        if T != 1:
            dout += '_' + str(T)
        # dout = os.path.join(dir, translation, lang)
        with tarfile.open(os.path.join(dout, 'd-domain.tgz'),
                          mode='w:gz') as tar:
            for domain in domains:
                # arcname = DOMAIN_NAMES[domain]
                arcname = domain + '.tsv'
                fullpath = os.path.join(dout, arcname)
                tar.add(fullpath, arcname=arcname)


def add_temperature(x, T):
    if x == 0 or x == 1:
        return x
    return 1 - 1 / (1 + math.pow(math.e, math.log(x / (1 - x)) / T))


if __name__ == '__main__':
    main()