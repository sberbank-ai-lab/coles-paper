# Get data

```sh
cd experiments/scenario_protein

# Check your ~/.kaggle/kaggle.json before data download
# download datasets
bin/get-data.sh

# convert datasets from transaction list to features for metric learning
bin/make-datasets-spark.sh
```

# Main scenario, best params

```sh
cd experiments/scenario_protein
export SC_DEVICE="cuda"

# Prepare Baselin agg feature encoder and take embedidngs; inference
python ../../metric_learning.py params.device="$SC_DEVICE" --conf conf/dataset.hocon conf/agg_features_params.json
python ../../ml_inference.py    params.device="$SC_DEVICE" --conf conf/dataset.hocon conf/agg_features_params.json


# Train a supervised model and save scores to the file
python -m scenario_protein fit_target \
    params.device="$SC_DEVICE" \
    params.labeled_amount=10000 params.train.n_epoch=20 \
    output.valid.path="data/target_scores_10K/valid" \
    output.test.path="data/target_scores_10K/test" \
    --conf conf/dataset.hocon conf/fit_target_params.json
python -m scenario_protein fit_target \
    params.device="$SC_DEVICE" \
    params.labeled_amount=20000 params.train.n_epoch=20 \
    output.valid.path="data/target_scores_20K/valid" \
    output.test.path="data/target_scores_20K/test" \
    --conf conf/dataset.hocon conf/fit_target_params.json
python -m scenario_protein fit_target \
    params.device="$SC_DEVICE" \
    params.labeled_amount=100000 params.train.n_epoch=20 \
    output.valid.path="data/target_scores_100K/valid" \
    output.test.path="data/target_scores_100K/test" \
    --conf conf/dataset.hocon conf/fit_target_params.json
python -m scenario_protein fit_target \
    params.device="$SC_DEVICE" \
    params.train.n_epoch=25 \
    output.valid.path="data/target_scores/valid" \
    output.test.path="data/target_scores/test" \
    --conf conf/dataset.hocon conf/fit_target_params.json


# Train the MeLES encoder and take embedidngs; inference
python ../../metric_learning.py params.device="$SC_DEVICE" --conf conf/dataset.hocon conf/mles_params.json
python ../../ml_inference.py    params.device="$SC_DEVICE" --conf conf/dataset.hocon conf/mles_params.json
#
# Fine tune the MLES model in supervised mode and save scores to the file
python -m scenario_protein fit_finetuning \
    params.device="$SC_DEVICE" \
    params.labeled_amount=10000 params.train.n_epoch=7 \
    output.valid.path="data/mles_finetuning_scores_10K/valid" \
    output.test.path="data/mles_finetuning_scores_10K/test" \
    --conf conf/dataset.hocon conf/fit_finetuning_on_mles_params.json
python -m scenario_protein fit_finetuning \
    params.device="$SC_DEVICE" \
    params.labeled_amount=20000 params.train.n_epoch=7 \
    output.valid.path="data/mles_finetuning_scores_20K/valid" \
    output.test.path="data/mles_finetuning_scores_20K/test" \
    --conf conf/dataset.hocon conf/fit_finetuning_on_mles_params.json
python -m scenario_protein fit_finetuning \
    params.device="$SC_DEVICE" \
    params.labeled_amount=100000 params.train.n_epoch=7 \
    output.valid.path="data/mles_finetuning_scores_100K/valid" \
    output.test.path="data/mles_finetuning_scores_100K/test" \
    --conf conf/dataset.hocon conf/fit_finetuning_on_mles_params.json
python -m scenario_protein fit_finetuning \
    params.device="$SC_DEVICE" \
    params.train.n_epoch=20 \
    output.valid.path="data/mles_finetuning_scores/valid" \
    output.test.path="data/mles_finetuning_scores/test" \
    --conf conf/dataset.hocon conf/fit_finetuning_on_mles_params.json


# Run estimation for different approaches
# Check some options with `--help` argument
python -m scenario_protein compare_approaches --n_workers 1 \
    --models lgb \
    --baseline_name "agg_feat_embed.pickle" \
    --embedding_file_names "mles_embedding.pickle" \
    --score_file_names "target_scores" "mles_finetuning_scores" \
        "target_scores_10K" "mles_finetuning_scores_10K" \
...
    --labeled_amount 10000


# check the results
cat results/scenario.csv
```

# CPC
```
# Train the Contrastive Predictive Coding (CPC) model; inference
python ../../train_cpc.py    dataset.max_rows=200000 params.device="$SC_DEVICE" --conf conf/dataset.hocon conf/cpc_params.json
python ../../ml_inference.py params.device="$SC_DEVICE" --conf conf/dataset.hocon conf/cpc_params.json
# Fine tune the CPC model in supervised mode and save scores to the file
python -m scenario_protein fit_finetuning params.device="$SC_DEVICE" --conf conf/dataset.hocon conf/fit_finetuning_on_cpc_params.json

```

# Fit target crop
```
python -m scenario_protein fit_target \
    params.device="$SC_DEVICE" \
    params.labeled_amount=10000 params.train.n_epoch=20 \
    params.train.clip_seq.min_len=250 params.train.clip_seq.max_len=600 \
    output.valid.path="data/target_scores_crop1_10K/valid" \
    output.test.path="data/target_scores_crop1_10K/test" \
    --conf conf/dataset.hocon conf/fit_target_params.json
python -m scenario_protein fit_target \
    params.device="$SC_DEVICE" \
    params.labeled_amount=10000 params.train.n_epoch=20 \
    params.train.clip_seq.min_len=400 params.train.clip_seq.max_len=600 \
    output.valid.path="data/target_scores_crop2_10K/valid" \
    output.test.path="data/target_scores_crop2_10K/test" \
    --conf conf/dataset.hocon conf/fit_target_params.json
python -m scenario_protein compare_approaches --n_workers 1 \
    --score_file_names "target_scores_crop1_10K" "target_scores_crop2_10K"

python -m scenario_protein fit_target \
    params.device="$SC_DEVICE" \
    params.labeled_amount=20000 params.train.n_epoch=20 \
    params.train.clip_seq.min_len=250 params.train.clip_seq.max_len=600 \
    output.valid.path="data/target_scores_crop1_20K/valid" \
    output.test.path="data/target_scores_crop1_20K/test" \
    --conf conf/dataset.hocon conf/fit_target_params.json
python -m scenario_protein fit_target \
    params.device="$SC_DEVICE" \
    params.labeled_amount=20000 params.train.n_epoch=20 \
    params.train.clip_seq.min_len=400 params.train.clip_seq.max_len=600 \
    output.valid.path="data/target_scores_crop2_20K/valid" \
    output.test.path="data/target_scores_crop2_20K/test" \
    --conf conf/dataset.hocon conf/fit_target_params.json
python -m scenario_protein compare_approaches --n_workers 1 \
    --score_file_names "target_scores_crop1_20K" "target_scores_crop2_20K"


python -m scenario_protein fit_target \
    params.device="$SC_DEVICE" \
    params.labeled_amount=100000 params.train.n_epoch=20 \
    params.train.num_workers=8 \
    params.train.clip_seq.min_len=250 params.train.clip_seq.max_len=600 \
    output.valid.path="data/target_scores_crop1_100K/valid" \
    output.test.path="data/target_scores_crop1_100K/test" \
    --conf conf/dataset.hocon conf/fit_target_params.json
python -m scenario_protein fit_target \
    params.device="$SC_DEVICE" \
    params.labeled_amount=100000 params.train.n_epoch=20 \
    params.train.num_workers=8 \
    params.train.clip_seq.min_len=400 params.train.clip_seq.max_len=600 \
    output.valid.path="data/target_scores_crop2_100K/valid" \
    output.test.path="data/target_scores_crop2_100K/test" \
    --conf conf/dataset.hocon conf/fit_target_params.json
python -m scenario_protein compare_approaches --n_workers 1 \
    --score_file_names "target_scores_crop1_100K" "target_scores_crop2_100K"


python -m scenario_protein fit_target \
    params.device="$SC_DEVICE" \
    params.train.n_epoch=25 \
    params.train.clip_seq.min_len=250 params.train.clip_seq.max_len=600 \
    params.train.lr=0.001 \
    output.valid.path="data/target_crop1_scores/valid" \
    output.test.path="data/target_crop1_scores/test" \
    --conf conf/dataset.hocon conf/fit_target_params.json
python -m scenario_protein fit_target \
    params.device="$SC_DEVICE" \
    params.train.n_epoch=25 \
    params.train.clip_seq.min_len=400 params.train.clip_seq.max_len=600 \
    output.valid.path="data/target_crop2_scores/valid" \
    output.test.path="data/target_crop2_scores/test" \
    --conf conf/dataset.hocon conf/fit_target_params.json
python -m scenario_protein compare_approaches --n_workers 2 \
    --score_file_names "target_crop1_scores" "target_crop2_scores"

```