#! /usr/bin/env python3

"""
Read a master XLSX workbook and output cram paths and json paths.
Read cram paths and run subprocess to output RGs, and then output RG barcodes
and samples. Parse JSON Merge objects and output merge barcodes and samples.
Compare cram RG barcodes and samples to JSON merge barcodes and samples.
"""

# First come standard libraries, in alphabetical order.
import argparse
from collections import Counter
import json
import logging
import os
from pathlib import Path
import pprint
import sys
from subprocess import run, DEVNULL, PIPE

# after a blank line, import third-party libraries.
import openpyxl
from openpyxl.styles import Font

# After another blank line, import local libraries.
from dump_js_barcodes import Merge
from dump_js_barcodes import SequencingEvent

__version__ = '1.0.0-working'

logger = logging.getLogger(__name__)


def main():
    args = parse_args()
    config_logging(args)
    run(args)
    logging.shutdown()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_file',
                        nargs='?',
                        type=argparse.FileType('rb'),
                        default=sys.stdin)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('--version', action='version',
                        version='%(prog)s {}'.format(__version__))
    args = parser.parse_args()
    return args


def config_logging(args):
    global logger
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level)
    logger = logging.getLogger('mplx_qc')


def run(args):
    logger.debug('args: %r', args)
    input_file = args.input_file
    process_input(input_file,)
    logger.debug('finished')


def process_input(input_file,):
    """A docsting should say something about the inputs and
    any compare results.  In this case there are no return results."""
    logger.debug('process_input %s -> %s', input_file,)
    merged_crams = read_input(input_file)
    logger.info('type: %s', type(merged_crams))
    logger.info('found %s records', len(merged_crams))
    pprint.pprint(vars(merged_crams[0]))
    pprint.pprint(vars(merged_crams[-1]))
    cram_paths = []
    json_paths = []
    for record in merged_crams:
        cram_paths.append(record.cram_path)
        json_paths.append(record.json_path)
    logger.info('type: %s, %s', type(cram_paths), type(json_paths))
    logger.info('found %s cram_paths, %s json_paths', len(cram_paths), len(json_paths))
    pprint.pprint('finally...')
    pprint.pprint(cram_paths[0]) 
    pprint.pprint(json_paths[0])
    return cram_paths, json_paths 
    process_crams(cram_paths)
    process_json_data(json_paths)
    compare_barcodes(cram_rg_barcodes, json_barcodes)  
                

def read_input(input_file):
    """Read master XLSX of merged CRAMs and return list of objects containing
    the file paths."""
    wb = openpyxl.load_workbook(filename=input_file)
    sheet = wb.get_sheet_by_name('smpls')
    active_sheet = wb.active
    assert sheet == active_sheet, (sheet.title, active_sheet.title)
    logger.debug('active_sheet name: %s', active_sheet.title)
    row_iter = iter(active_sheet.rows)
    header_row = next(row_iter)
    column_names = [c.value for c in header_row]
    logger.debug('columns: %s', column_names)
    merged_crams = []
    for row in row_iter:
        merged_cram = Generic()
        for column_name, cell in zip(column_names, row):
            if column_name in ['json_path', 'cram_path']:
                value = cell.value
                setattr(merged_cram, column_name, value)
        merged_crams.append(merged_cram)
    return merged_crams


def process_crams(cram_paths):
    """Read cram_paths, run samtools to parse
    CRAM barcodes and samples"""
    logger.debug('seching: %s', cram_paths)
    rgs_list = dump_cram_rgs(cram_paths)
    for line in rgs_list:
        linesplit = line.rstrip().split('\t')
        if linesplit[0] != '@RG':
            continue
        rg_dict = {}
        for item in linesplit[1:]:
            k, v = item.split(':', 1)
            assert ':' not in k
        rg_dict[k] = v
        cram_rg_barcodes = rg_dict['PU']
        cram_rg_samples = rg_dict['SM']
        print(cram_rg_barcodes, cram_rg_samples, sep='\t')


def dump_cram_rgs(cram_paths):
    cram_paths = [l.strip() for l in fin]
    rgs_list = []
    for file in cram_paths:
        cp = run(['samtools', 'view', '-H', file], stdin=DEVNULL, stdout=PIPE, universal_newlines=True, check=True)
        cp.stdout.splitlines
        headers = cp.stdout.splitlines()
        rgs = [h for h in headers if h.startswith('@RG\t')]
        rgs_list = '\n'.join(rgs)
    return rgs_list


def process_json_data(json_paths):
    """from dump_js_barcodes.py import Merge,
    and parse JSON merge barcodes and JSON merge samples"""
    logger.debug('seaching: %s', json_paths)
    for merge in parse_merge_definition(json_path_stream):
        for s in merge.sequencing_events:
            row = [s.barcode, s.sample_name]
            print(*row, sep='\t')
    

def parse_merge_definition(json_path_stream):
    """json_path_stream is also known as json_paths, 
    Generator of Merge objects."""
    logger.debug('generating %s', 'Merge objects')
    for line in json_path_stream:
        json_path = line.rstrip('\n')
        merge = Merge(json_path)
        yield merge


def compare_barcodes(cram_rg_barcodes, json_barcodes):
    """Compare a set of CRAM RG barcodes, samples to
    JSON barcodes, samples"""
    logger.debug('searching: %s and %s', cram_rg_barcodes, json_barcodes)
    assert set(cram_rg_barcodes) == set(json_barcodes)
    return (
            set(cram_rg_barcodes) == set(json_barcodes) and
            len(cram_rg_barcodes) == len(json_barcodes)
            )


class Generic:
    """To create objects with __dict__."""
    pass


if __name__ == '__main__':
    main()
