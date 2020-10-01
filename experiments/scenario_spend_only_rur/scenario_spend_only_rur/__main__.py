import argparse
import logging
import numpy as np
import torch

if __name__ == '__main__':
    import sys
    sys.path.append('../../')

    # reproducibility
    from dltranz.util import switch_reproducibility_on
    switch_reproducibility_on()


from scenario_spend_only_rur import fit_on_embeddings
from scenario_spend_only_rur import compare_approaches

logger = logging.getLogger(__name__)


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    for module in [compare_approaches, fit_on_embeddings]:
        sub_parser = subparsers.add_parser(module.__name__.split('.')[-1])
        sub_parser.set_defaults(func=module.main)
        module.prepare_parser(sub_parser)

    config, _ = parser.parse_known_args(args)
    return vars(config)


if __name__ == '__main__':
    conf = parse_args()
    if 'func' not in conf:
        print('Choose scenario. Use --help for more information')
        exit(-1)

    conf['func'](conf)
