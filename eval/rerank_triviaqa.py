import argparse
import pandas as pd
import numpy as np
from tqdm import tqdm

from data_processing.document_splitter import TopTfIdf, MergeParagraphs, ShallowOpenWebRanker
from data_processing.preprocessed_corpus import preprocess_par
from data_processing.text_utils import NltkPlusStopWords
from trivia_qa.build_span_corpus import TriviaQaWebDataset, TriviaQaOpenDataset
from trivia_qa.training_data import ExtractMultiParagraphs, ExtractMultiParagraphsPerQuestion
from utils import flatten_iterable, print_table


def compute_model_scores(df, max_over, target_score, group_cols):
    scores = []
    for _, group in df[[max_over, target_score] + group_cols].groupby(group_cols):
        if target_score == max_over:
            scores.append(group[target_score].cummax().values)
        else:
            used_predictions = group[max_over].expanding().apply(lambda x: x.argmax())
            scores.append(group[target_score].iloc[used_predictions].values)

    max_para = max(len(x) for x in scores)
    summed_scores = np.zeros(max_para)
    for s in scores:
        summed_scores[:len(s)] += s
        summed_scores[len(s):] += s[-1]
    return summed_scores/len(scores)


def show_scores_table(df, n_to_show, cols):
    rows = [["Rank"] + cols]
    n_to_show = min(n_to_show, len(df))
    for i in range(n_to_show):
        rows.append(["%d" % (i+1)] + ["%.4f" % df[k].iloc[i] for k in cols])
    print_table(rows)


def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('answers', help='answer file', nargs="+")
    parser.add_argument('--open', action="store_true")
    args = parser.parse_args()

    print("Loading answers..")
    answer_dfs = []
    for filename in args.answers:
        answer_dfs.append(pd.read_csv(filename))

    print("Loading questions..")
    if args.open:
        corpus = TriviaQaOpenDataset()
    else:
        corpus = TriviaQaWebDataset()

    questions = corpus.get_dev()
    quids = set()
    for df in answer_dfs:
        quids.update(df.question_id)
    questions = [q for q in questions if q.question_id in quids]

    print("Computing ranks..")
    # if args.open:
    #     pre = ExtractMultiParagraphsPerQuestion(MergeParagraphs(400), ShallowOpenWebRanker(50), None, require_an_answer=False)
    # else:
    #     pre = ExtractMultiParagraphs(MergeParagraphs(400), TopTfIdf(NltkPlusStopWords(), 1000), None, require_an_answer=False)
    #
    # mcs = preprocess_par(questions, corpus.evidence, pre, 6, 10000).data
    #
    # ranks = {}
    # for mc in mcs:
    #     for i, para in enumerate(mc.paragraphs):
    #         ranks[(mc.question_id, para.doc_id, para.start, para.end)] = i

    data = {}
    for i, answer_df in enumerate(answer_dfs):
        # ranks_col = []
        # for t in answer_df[["question_id", "doc_id", "para_start", "para_end"]].itertuples(index=False):
        #     ranks_col.append(ranks[t])
        # answer_df["rank"] = answer_dfs["rank"]
        #
        # print("Scoring...")
        # answer_df.sort_values(["ranks"], inplace=True)
        answer_df.sort_values(["rank"], inplace=True)
        # answer_df["none_prob"] = -answer_df["none_prob"]
        model_scores = compute_model_scores(answer_df, "predicted_score", "text_f1",
                                            ["question_id"] if args.open else ["question_id", "doc_id"])
        data["answers_%d" % i] = model_scores

    show_scores_table(pd.DataFrame(data), 30 if args.open else 12, list(data.keys()))


if __name__ == "__main__":
    main()


