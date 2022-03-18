# CFR-Jr

Code for the paper "Learning to Correlate in Multi-Player General-Sum Sequential Games" (published on [ariXiv](https://arxiv.org/abs/1910.06228) and [NeurIPS](https://nips.cc/Conferences/2019/AcceptedPapersInitial)).

## Usage

The entry point of the code is the python script `runner.py`.
It currently supports `{CFR, CFR+, CFR-S, CFR-Jr}` as regret-minimization algorithms, which can be run on instances of the the games of `{Kuhn, Leduc, Goofspiel, Random, Hanabi}`.

Run the command `python runner.py --help` for more detailed information on the usage.