import argparse
import pandas as pd
import numpy as np
from tqdm import tqdm

from data_processing.text_utils import NltkPlusStopWords
from squad.squad_data import SquadCorpus
from squad.squad_document_qa import SquadTfIdfRanker
from utils import flatten_iterable, print_table


def compute_model_scores(df, max_over, target_score, group_cols):
    scores = []
    for _, group in df.groupby(group_cols):
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


def show_scores_table(scores, n_to_show=10):
    rows = [["Rank"] + ["Score"]]
    n_to_show = min(n_to_show, len(scores))
    for i in range(n_to_show):
        rows.append(["%d" % (i+1)] + ["%.4f" % scores.iloc[i]])
    print_table(rows)


def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('answers', help='answer file')
    args = parser.parse_args()

    print("Loading answers..")
    answer_df = pd.read_csv(args.answers)

    print("Scoring...")
    answer_df.sort_values(["rank"], inplace=True)
    model_scores = compute_model_scores(answer_df, "predicted_score", "text_f1", ["question_id"])
    print(model_scores)
    show_scores_table(pd.DataFrame({"model_score": model_scores}), 12)


if __name__ == "__main__":
    main()


