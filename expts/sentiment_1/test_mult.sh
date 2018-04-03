python ../scripts/discriminative_driver.py --datasets LMRD SSTb --dataset_paths data/tf/merged/LMRD_SSTb/min_50_max_-1/LMRD/ data/tf/merged/LMRD_SSTb/min_50_max_-1/SSTb/ --class_sizes 2 5 --vocab_path data/tf/merged/LMRD_SSTb/min_50_max_-1/vocab_size.txt --encoder_config_file encoders.json --model mult --input_key tokens --architecture paragram --alphas 0.5 0.5 --mode test --checkpoint_dir ./data/ckpt/SSTb_LMRD/