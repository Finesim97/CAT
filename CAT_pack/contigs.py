#!/usr/bin/env python3

import argparse
import datetime
import multiprocessing
import os
import sys

import about
import check
import shared
import tax


def parse_arguments():
    parser = argparse.ArgumentParser(prog='CAT contigs',
                                     description='Run Contig Annotation Tool '
                                                 '(CAT).',
                                     usage='CAT contigs -c -d -t '
                                           '[options] [-h / --help]',
                                     add_help=False)
    
    required = parser.add_argument_group('Required arguments')
    
    required.add_argument('-c',
                          '--contigs_fasta',
                          dest='contigs_fasta',
                          metavar='',
                          required=True,
                          type=str,
                          help='Path to contigs fasta file.')
    required.add_argument('-d',
                          '--database_folder',
                          dest='database_folder',
                          metavar='',
                          required=True,
                          type=str,
                          help='Path to folder that contains database files.')
    required.add_argument('-t',
                          '--taxonomy_folder',
                          dest='taxonomy_folder',
                          metavar='',
                          required=True,
                          type=str,
                          help='Path to folder that contains taxonomy files.')
    
    optional = parser.add_argument_group('Optional arguments')
    
    optional.add_argument('-r',
                          '--range',
                          dest='r',
                          metavar='',
                          required=False,
                          type=float,
                          choices = [i for i in range(50)],
                          default=10,
                          help='r parameter [0-49] (default: 10).')
    optional.add_argument('-f',
                          '--fraction',
                          dest='f',
                          metavar='',
                          required=False,
                          type=float,
                          choices = [i / 100 for i in range(0, 100)],
                          default=0.5,
                          help='f parameter [0-0.99] (default: 0.5).')
    optional.add_argument('-o',
                          '--out_prefix',
                          dest='out_prefix',
                          metavar='',
                          required=False,
                          type=str,
                          default='out.CAT',
                          help='Prefix for output files (default: out.CAT).')
    optional.add_argument('-p',
                          '--proteins_fasta',
                          dest='predicted_proteins_fasta',
                          metavar='',
                          required=False,
                          type=str,
                          help='Path to predicted proteins fasta file. If '
                               'supplied, CAT will skip the protein '
                               'prediction step.')
    optional.add_argument('-a',
                          '--diamond_alignment',
                          dest='diamond_file',
                          metavar='',
                          required=False,
                          type=str,
                          help='Path to DIAMOND alignment table. If supplied, '
                               'CAT will skip the DIAMOND alignment step and '
                               'directly classify the contigs. A predicted '
                               'proteins fasta file should also be supplied '
                               'with argument [-p / --proteins].')
    optional.add_argument('--path_to_prodigal',
                          dest='path_to_prodigal',
                          metavar='',
                          required=False,
                          type=str,
                          default='prodigal',
                          help='Path to Prodigal binaries. Please supply if '
                               'CAT can not find Prodigal.')
    optional.add_argument('--path_to_diamond',
                          dest='path_to_diamond',
                          metavar='',
                          required=False,
                          type=str,
                          default='diamond',
                          help='Path to DIAMOND binaries. Please supply if '
                               'CAT can not find DIAMOND.')
    optional.add_argument('--no_stars',
                          dest='no_stars',
                          required=False,
                          action='store_true',
                          help='Suppress marking of suggestive '
                               'classifications.')
    optional.add_argument('-z',
                          '--compress',
                          dest='compress',
                          required=False,
                          action='store_true',
                          help='Compress output files.')
    optional.add_argument('--force',
                          dest='force',
                          required=False,
                          action='store_true',
                          help='Force overwrite existing files.')
    optional.add_argument('-q',
                          '--quiet',
                          dest='quiet',
                          required=False,
                          action='store_true',
                          help='Suppress verbosity.')
    optional.add_argument('--no_log',
                          dest='no_log',
                          required=False,
                          action='store_true',
                          help='Suppress log file.')
    optional.add_argument('-h',
                          '--help',
                          action='help',
                          help='Show this help message and exit.')
    optional.add_argument('--I_know_what_Im_doing',
                          dest='I_know_what_Im_doing',
                          required=False,
                          action='store_true',
                          help='Flag for experimental features.')
    
    specific = parser.add_argument_group('DIAMOND specific optional arguments')

    specific.add_argument('-n',
                          '--nproc',
                          dest='nproc',
                          metavar='',
                          required=False,
                          type=int,
                          default=multiprocessing.cpu_count(),
                          help='Number of cores to deploy by DIAMOND '
                               '(default: maximum).')
    specific.add_argument('--sensitive',
                          dest='sensitive',
                          required=False,
                          action='store_true',
                          help='Run DIAMOND in sensitive mode '
                               '(default: not enabled).')
    specific.add_argument('--block_size',
                          dest='block_size',
                          metavar='',
                          required=False,
                          type=float,
                          default=2.0,
                          help='DIAMOND block-size parameter (default: 2.0). '
                               'Lower numbers will decrease memory and '
                               'temporary disk space usage.')
    specific.add_argument('--index_chunks',
                          dest='index_chunks',
                          metavar='',
                          required=False,
                          type=int,
                          default=4,
                          help='DIAMOND index-chunks parameter (default: 4). '
                               'Set to 1 on high memory machines. The '
                               'parameter has no effect on temporary disk '
                               'space usage.')
    specific.add_argument('--tmpdir',
                          dest='tmpdir',
                          metavar='',
                          required=False,
                          type=str,
                          help='Directory for temporary DIAMOND files '
                               '(default: directory to which output files are '
                               'written).')
    specific.add_argument('--top',
                          dest='top',
                          metavar='',
                          required=False,
                          type=float,
                          choices = [i for i in range(51)],
                          default=50,
                          help='DIAMOND top parameter [0-50] (default: 50). '
                               'Governs hits within range of best hit that '
                               'are written to the alignment file. This is '
                               'not the [-r / --range] parameter! Can only be '
                               'set with the [--I_know_what_Im_doing] flag, '
                               'see README.md.')
                          
    (args, extra_args) = parser.parse_known_args()
    
    extra_args = [arg for (i, arg) in enumerate(extra_args) if
                  (i, arg) != (0, 'contigs')]
    if len(extra_args) > 0:
        sys.exit('error: too much arguments supplied:\n{0}'
                 ''.format('\n'.join(extra_args)))

    # Check experimental features.
    if not args.I_know_what_Im_doing:
        if args.top < 50:
            sys.exit('error: --top can only be set lower than 50 in '
                     'combination with the --I_know_what_Im_doing flag. See '
                     'README.md as to why this is the case.')
            
    return args


def contigs(args):
    step_list = []

    (contigs_fasta,
     database_folder,
     taxonomy_folder,
     r,
     one_minus_r,
     f,
     out_prefix,
     predicted_proteins_fasta,
     diamond_file,
     path_to_prodigal,
     path_to_diamond,
     no_stars,
     compress,
     force,
     quiet,
     no_log,
     nproc,
     sensitive,
     block_size,
     index_chunks,
     tmpdir,
     top) = check.convert_arguments(args)

    if no_log:
        log_file = None
    else:
        # Check out_prefix already as the log file needs to be written to a
        # valid location.
        error = check.check_out_prefix(out_prefix, None, quiet)
        if error:
            sys.exit(1)

        log_file = '{0}.log'.format(out_prefix)
        with open(log_file, 'w') as outf1:
            pass
        
    message = '# CAT v{0}.'.format(about.__version__)
    shared.give_user_feedback(message, log_file, quiet, show_time=False)
    
    # Check at which state to start.
    if predicted_proteins_fasta is None and diamond_file is None:
        message = ('\n'
                   'CAT is running. Protein prediction, alignment, and contig '
                   'classification are carried out.\n'
                   'Rarw!\n\n'
                   'Supplied command: {0}\n\n'
                   'Contigs fasta: {1}\n'
                   'Taxonomy folder: {2}/\n'
                   'Database folder: {3}/\n'
                   'Parameter r: {4}\n'
                   'Parameter f: {5}\n'
                   'Log file: {6}\n\n'
                   '-----------------\n'.format(' '.join(sys.argv),
                                                contigs_fasta,
                                                taxonomy_folder,
                                                database_folder,
                                                args.r,
                                                args.f,
                                                log_file))
        shared.give_user_feedback(message, log_file, quiet, show_time=False)

        step_list.append('run_prodigal')
        step_list.append('run_diamond')
    elif (predicted_proteins_fasta is not None
          and diamond_file is None):
        message = ('\n'
                   'CAT is running. Since a predicted protein fasta is '
                   'supplied, only alignment and contig classification are '
                   'carried out.\n'
                   'Rarw!\n\n'
                   'Supplied command: {0}\n\n'
                   'Contigs fasta: {1}\n'
                   'Taxonomy folder: {2}/\n'
                   'Database folder: {3}/\n'
                   'Parameter r: {4}\n'
                   'Parameter f: {5}\n'
                   'Log file: {6}\n\n'
                   '-----------------\n'.format(' '.join(sys.argv),
                                                contigs_fasta,
                                                taxonomy_folder,
                                                database_folder,
                                                args.r,
                                                args.f,
                                                log_file))
        shared.give_user_feedback(message, log_file, quiet, show_time=False)

        step_list.append('run_diamond')
    elif (predicted_proteins_fasta is not None and
          diamond_file is not None):
        message = ('\n'
                   'CAT is running. Since a predicted protein fasta and '
                   'DIAMOND alignment file are supplied, only contig '
                   'classification is carried out.\n'
                   'Rarw!\n\n'
                   'Supplied command: {0}\n\n'
                   'Contigs fasta: {1}\n'
                   'Taxonomy folder: {2}/\n'
                   'Database folder: {3}/\n'
                   'Parameter r: {4}\n'
                   'Parameter f: {5}\n'
                   'Log file: {6}\n\n'
                   '-----------------\n'.format(' '.join(sys.argv),
                                                contigs_fasta,
                                                taxonomy_folder,
                                                database_folder,
                                                args.r,
                                                args.f,
                                                log_file))
        shared.give_user_feedback(message, log_file, quiet, show_time=False)
    elif (predicted_proteins_fasta is None and
          diamond_file is not None):
        message = ('ERROR: if you want CAT to directly do the classification, '
                   'you should not only supply a DIAMOND alignment table but '
                   'also a predicted protein fasta file with argument '
                   '[-p / --proteins].')
        shared.give_user_feedback(message, log_file, quiet, error=True)

        sys.exit(1)

    # Check binaries, output files, taxonomy folder and database folder, and
    # set parameters.
    message = 'Doing some pre-flight checks first.'
    shared.give_user_feedback(message, log_file, quiet, show_time=False)

    errors = []

    errors.append(check.check_out_prefix(out_prefix, log_file, quiet))

    if 'run_prodigal' in step_list:
        errors.append(check.check_prodigal_binaries(path_to_prodigal,
                                                    log_file,
                                                    quiet))

        predicted_proteins_fasta = ('{0}.predicted_proteins.faa'
                                    ''.format(out_prefix))
        predicted_proteins_gff = ('{0}.predicted_proteins.gff'
                                  ''.format(out_prefix))

        if not force:
            errors.append(check.check_output_file(predicted_proteins_fasta,
                                                  log_file,
                                                  quiet))
            errors.append(check.check_output_file(predicted_proteins_gff,
                                                  log_file,
                                                  quiet))
    
    compress_suffix = ".gz" if compress else ""

    if 'run_diamond' in step_list:
        errors.append(check.check_diamond_binaries(path_to_diamond,
                                                   log_file,
                                                   quiet))

        diamond_file = '{0}.alignment.diamond{1}'.format(out_prefix, compress_suffix)
        
        if not force:
            errors.append(check.check_output_file(diamond_file,
                                                  log_file,
                                                  quiet))
    else:
        diamond_file = diamond_file
        
    errors.append(check.check_folders_for_run(taxonomy_folder,
                                              database_folder,
                                              step_list,
                                              log_file,
                                              quiet))
    
    contig2classification_output_file = ('{0}.contig2classification.txt{1}'
                                         ''.format(out_prefix, compress_suffix))
    ORF2LCA_output_file = '{0}.ORF2LCA.txt{1}'.format(out_prefix, compress_suffix)

    if not force:
        errors.append(check.check_output_file(contig2classification_output_file,
                                              log_file,
                                              quiet))
        errors.append(check.check_output_file(ORF2LCA_output_file,
                                              log_file,
                                              quiet))

    if 'run_prodigal' not in step_list:
        if not check.check_whether_file_is_fasta(predicted_proteins_fasta):
            message = ('ERROR: {0} is not a fasta file.'
                       ''.format(predicted_proteins_fasta))
            shared.give_user_feedback(message, log_file, quiet, error=True)

            errors.append(True)

    errors.append(check.check_top(top, r, log_file, quiet))
    
    if True in errors:
        sys.exit(1)
        
    (nodes_dmp,
     names_dmp,
     prot_accession2taxid_file) = check.inspect_taxonomy_folder(taxonomy_folder)
    (nr_file,
     diamond_database,
     fastaid2LCAtaxid_file,
     taxids_with_multiple_offspring_file) = check.inspect_database_folder(database_folder)
    
    message = 'Ready to fly!\n\n-----------------\n'
    shared.give_user_feedback(message, log_file, quiet, show_time=False)
    
    # Start CAT.
    contig_names = shared.import_contig_names(contigs_fasta, log_file, quiet)
    
    if 'run_prodigal' in step_list:
        shared.run_prodigal(path_to_prodigal,
                            contigs_fasta,
                            predicted_proteins_fasta,
                            predicted_proteins_gff,
                            tmpdir,
                            log_file,
                            quiet)
        
    contig2ORFs = shared.import_ORFs(predicted_proteins_fasta, log_file, quiet)
    
    check.check_whether_ORFs_are_based_on_contigs(contig_names,
                                                  contig2ORFs,
                                                  log_file,
                                                  quiet)
    
    if 'run_diamond' in step_list:
        shared.run_diamond(path_to_diamond,
                           diamond_database,
                           predicted_proteins_fasta,
                           diamond_file,
                           nproc,
                           sensitive,
                           block_size,
                           index_chunks,
                           tmpdir,
                           top,
                           log_file,
                           compress,
                           quiet)
        
    (ORF2hits,
     all_hits) = shared.parse_diamond_file(diamond_file,
                                           one_minus_r,
                                           log_file,
                                           quiet)

    (taxid2parent, taxid2rank) = tax.import_nodes(nodes_dmp, log_file, quiet)
    fastaid2LCAtaxid = tax.import_fastaid2LCAtaxid(fastaid2LCAtaxid_file,
                                                   all_hits,
                                                   log_file,
                                                   quiet)
    taxids_with_multiple_offspring = tax.import_taxids_with_multiple_offspring(taxids_with_multiple_offspring_file,
                                                                               log_file,
                                                                               quiet)

    message = ('CAT is spinning! Files {0} and {1} are created.'
               ''.format(contig2classification_output_file,
                         ORF2LCA_output_file))
    shared.give_user_feedback(message, log_file, quiet)

    number_of_classified_contigs = 0
    
    with shared.open_maybe_gzip(contig2classification_output_file, 'wt') as outf1, shared.open_maybe_gzip(ORF2LCA_output_file, 'wt') as outf2:
        outf1.write('# contig\tclassification\treason\tlineage\t'
                    'lineage scores\n')
        outf2.write('# ORF\tlineage\tbit-score\n')
        
        for contig in sorted(contig_names):
            if contig not in contig2ORFs:
                outf1.write('{0}\tunclassified\tno ORFs found\n'
                            ''.format(contig))
                
                continue

            LCAs_ORFs = []

            for ORF in contig2ORFs[contig]:
                if ORF not in ORF2hits:
                    outf2.write('{0}\tORF has no hit to database\n'
                                ''.format(ORF))

                    continue
                
                (taxid,
                 top_bitscore) = tax.find_LCA_for_ORF(ORF2hits[ORF],
                                                      fastaid2LCAtaxid,
                                                      taxid2parent)
                 
                if taxid.startswith('no taxid found'):
                    outf2.write('{0}\t{1}\t{2}\n'.format(ORF,
                                                         taxid,
                                                         top_bitscore))
                else:
                    lineage = tax.find_lineage(taxid, taxid2parent)

                    if not no_stars:
                        lineage = tax.star_lineage(lineage,
                                                   taxids_with_multiple_offspring)
                    
                    outf2.write('{0}\t{1}\t{2}\n'
                                ''.format(ORF,
                                          ';'.join(lineage[::-1]),
                                          top_bitscore))
                                   
                LCAs_ORFs.append((taxid, top_bitscore),)
                
            if len(LCAs_ORFs) == 0:
                outf1.write('{0}\tunclassified\tno hits to database\n'
                            ''.format(contig))

                continue

            (lineages,
             lineages_scores,
             based_on_number_of_ORFs) = tax.find_weighted_LCA(LCAs_ORFs,
                                                              taxid2parent,
                                                              f)
             
            if lineages == 'no ORFs with taxids found.':
                outf1.write('{0}\tunclassified\t'
                            'hits not found in taxonomy files\n'
                            ''.format(contig))

                continue
            
            if lineages == 'no lineage whitelisted.':
                outf1.write('{0}\tunclassified\t'
                            'no lineage reached minimum bit-score support\n'
                            ''.format(contig))

                continue

            # The contig has a valid classification.
            number_of_classified_contigs += 1

            for (i, lineage) in enumerate(lineages):
                if not no_stars:
                    lineage = tax.star_lineage(lineage,
                                               taxids_with_multiple_offspring)
                scores = ['{0:.2f}'.format(score) for score in
                          lineages_scores[i]]
                
                if len(lineages) == 1:
                    # There is only one classification.
                    outf1.write('{0}\tclassified\t'
                                'based on {1}/{2} ORFs\t{3}\t{4}\n'
                                ''.format(contig,
                                          based_on_number_of_ORFs,
                                          len(contig2ORFs[contig]),
                                          ';'.join(lineage[::-1]),
                                          ';'.join(scores[::-1])))
                else:
                    # There are multiple classifications.
                    outf1.write('{0}\tclassified ({1}/{2})\t'
                                'based on {3}/{4} ORFs\t{5}\t{6}\n'
                                ''.format(contig,
                                          i + 1,
                                          len(lineages),
                                          based_on_number_of_ORFs,
                                          len(contig2ORFs[contig]),
                                          ';'.join(lineage[::-1]),
                                          ';'.join(scores[::-1])))

    message = ('\n-----------------\n\n'
               '[{0}] CAT is done! {1}/{2} contigs classified.'
               ''.format(datetime.datetime.now(),
                         number_of_classified_contigs,
                         len(contig_names)))
    shared.give_user_feedback(message, log_file, quiet, show_time=False)

    if f < 0.5:
        message = ('\nWARNING: since f is set to smaller than 0.5, one '
                   'contig may have multiple classifications.')
        shared.give_user_feedback(message, log_file, quiet, show_time=False)


def run():
    args = parse_arguments()

    contigs(args)


if __name__ == '__main__':
    sys.exit('Please run \'CAT contigs\' to run Contig Annotation Tool (CAT).')
