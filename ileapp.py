import argparse
import io
import os.path
import typing
import plugin_loader
import scripts.report as report
import traceback
from scripts.search_files import *
from scripts.ilapfuncs import *
from scripts.version_info import aleapp_version
from time import process_time, gmtime, strftime, perf_counter

def main():
    parser = argparse.ArgumentParser(description='iLEAPP: iOS Logs, Events, and Plists Parser.')
    parser.add_argument('-t', choices=['fs','tar','zip', 'gz', 'itunes'], required=False, action="store", 
                        help="Input type (fs = extracted to file system folder)")
    parser.add_argument('-o', '--output_path', required=False, action="store", help='Output folder path')
    parser.add_argument('-i', '--input_path', required=False, action="store", help='Path to input file/folder')
    parser.add_argument('-p', '--artifact_paths', required=False, action="store_true", 
                        help='Text file list of artifact paths')
    parser.add_argument('-w', '--wrap_text', required=False, action="store_false",
                        help='do not wrap text for output of data files')

    loader = plugin_loader.PluginLoader()

    print(f"Info: {len(loader)} plugins loaded.")

    args = parser.parse_args()

    if args.artifact_paths:
        print('Artifact path list generation started.')
        print('')
        with open('path_list.txt', 'a') as paths:
            for plugin in loader.plugins:
                if isinstance(plugin.search, tuple):
                    for x in plugin.search:
                        paths.write(x+'\n')
                        print(x)
                else:  # TODO check that this is actually a string?
                    paths.write(plugin.search+'\n')
                    print(plugin.search)
        print('')
        print('Artifact path list generation completed')    
        return

    else:
        input_path = args.input_path
        extracttype = args.t

        wrap_text = True if args.wrap_text is None else args.wrap_text
        if args.output_path is None:
            parser.error('No OUTPUT folder path provided')
            return
        else:
            output_path = os.path.abspath(args.output_path)

        if output_path is None:
            parser.error('No OUTPUT folder selected. Run the program again.')
            return

        if input_path is None:
            parser.error('No INPUT file or folder selected. Run the program again.')
            return

        if args.t is None:
            parser.error('No INPUT file or folder selected. Run the program again.')
            return

        if not os.path.exists(input_path):
            parser.error('INPUT file/folder does not exist! Run the program again.')
            return

        if not os.path.exists(output_path):
            parser.error('OUTPUT folder does not exist! Run the program again.')
            return  

        # ios file system extractions contain paths > 260 char, which causes problems
        # This fixes the problem by prefixing \\?\ on each windows path.
        if is_platform_windows():
            if input_path[1] == ':' and extracttype =='fs': input_path = '\\\\?\\' + input_path.replace('/', '\\')
            if output_path[1] == ':': output_path = '\\\\?\\' + output_path.replace('/', '\\')

        out_params = OutputParameters(output_path)

        crunch_artifacts(list(loader.plugins), extracttype, input_path, out_params, 1, wrap_text, loader)


def crunch_artifacts(
        plugins: typing.Sequence[plugin_loader.PluginSpec], extracttype, input_path, out_params, ratio, wrap_text,
        loader: plugin_loader.PluginLoader):
    start = process_time()
    start_wall = perf_counter()

    logfunc('Processing started. Please wait. This may take a few minutes...')

    logfunc('\n--------------------------------------------------------------------------------------')
    logfunc(f'iLEAPP v{aleapp_version}: iLEAPP Logs, Events, and Properties Parser')
    logfunc('Objective: Triage iOS Full System Extractions.')
    logfunc('By: Alexis Brignoni | @AlexisBrignoni | abrignoni.com')
    logfunc('By: Yogesh Khatri   | @SwiftForensics | swiftforensics.com')
    logdevinfo()

    seeker = None
    try:
        if extracttype == 'fs':
            seeker = FileSeekerDir(input_path)

        elif extracttype in ('tar', 'gz'):
            seeker = FileSeekerTar(input_path, out_params.temp_folder)

        elif extracttype == 'zip':
            seeker = FileSeekerZip(input_path, out_params.temp_folder)

        elif extracttype == 'itunes':
            seeker = FileSeekerItunes(input_path, out_params.temp_folder)

        else:
            logfunc('Error on argument -o (input type)')
            return False
    except Exception as ex:
        logfunc('Had an exception in Seeker - see details below. Terminating Program!')
        temp_file = io.StringIO()
        traceback.print_exc(file=temp_file)
        logfunc(temp_file.getvalue())
        temp_file.close()
        return False

    # Now ready to run
    logfunc(f'Artifact categories to parse: {len(plugins)}')
    logfunc(f'File/Directory selected: {input_path}')
    logfunc('\n--------------------------------------------------------------------------------------')

    with open(os.path.join(out_params.report_folder_base, 'Script Logs', 'ProcessedFilesLog.html'), 'w+', encoding='utf8') as log:
        nl = '\n' #literal in order to have new lines in fstrings that create text files
        log.write(f'Extraction/Path selected: {input_path}<br><br>')

        categories_searched = 0
        # Special processing for iTunesBackup Info.plist as it is a seperate entity, not part of the Manifest.db. Seeker won't find it
        if extracttype == 'itunes':
            info_plist_path = os.path.join(input_path, 'Info.plist')
            if os.path.exists(info_plist_path):
                # process_artifact([info_plist_path], 'iTunesBackupInfo', 'Device Info', seeker, out_params.report_folder_base)
                #plugin.method([info_plist_path], out_params.report_folder_base, seeker, wrap_text)
                loader["iTunesBackupInfo"].method([info_plist_path], out_params.report_folder_base, seeker, wrap_text)
                #del search_list['lastBuild'] # removing lastBuild as this takes its place
                print([info_plist_path])  # TODO Remove special consideration for itunes? Merge into main search
            else:
                logfunc('Info.plist not found for iTunes Backup!')
                log.write('Info.plist not found for iTunes Backup!')
            categories_searched += 1
            GuiWindow.SetProgressBar(categories_searched * ratio)

            # Search for the files per the arguments
        for plugin in plugins:
            artifact_pretty_name = plugin.name
            if isinstance(plugin.search, (list, tuple)):
                search_regexes = plugin.search
            else:
                search_regexes = [plugin.search]
            files_found = []
            for artifact_search_regex in search_regexes:
                if found := seeker.search(artifact_search_regex):
                    for pathh in found:
                        if pathh.startswith('\\\\?\\'):
                            pathh = pathh[4:]
                        log.write(f'Files for {artifact_search_regex} located at {pathh}<br><br>')
                    files_found.extend(found)
                else:
                    log.write(f'No files found for {plugin.name} -> {artifact_search_regex}<br><br>')
            if files_found:
                logfunc(f'{plugin.name} [{plugin.module_name}] artifact started')
                category_folder = os.path.join(out_params.report_folder_base, plugin.category)
                if not os.path.exists(category_folder):
                    try:
                        os.mkdir(category_folder)
                    except (FileExistsError, FileNotFoundError) as ex:
                        logfunc(
                            f'Error creating {plugin.name} report directory at path {category_folder}'
                        )

                        logfunc(f'Error was {str(ex)}')
                        continue  # cannot do work
                try:
                    plugin.method(files_found, category_folder, seeker, wrap_text)
                except Exception as ex:
                    logfunc(f'Reading {plugin.name} artifact had errors!')
                    logfunc(f'Error was {str(ex)}')
                    logfunc(f'Exception Traceback: {traceback.format_exc()}')
                    continue  # nope

                logfunc(f'{plugin.name} [{plugin.module_name}] artifact completed')
                logfunc('')

            categories_searched += 1
            GuiWindow.SetProgressBar(categories_searched * ratio)
    logfunc('')
    logfunc('Processes completed.')
    end = process_time()
    end_wall = perf_counter()
    run_time_secs =  end - start
    run_time_HMS = strftime('%H:%M:%S', gmtime(run_time_secs))
    logfunc(f"Processing time = {run_time_HMS}")
    run_time_secs =  end_wall - start_wall
    run_time_HMS = strftime('%H:%M:%S', gmtime(run_time_secs))
    logfunc(f"Processing time (wall)= {run_time_HMS}")

    logfunc('')
    logfunc('Report generation started.')
    # remove the \\?\ prefix we added to input and output paths, so it does not reflect in report
    if is_platform_windows(): 
        if out_params.report_folder_base.startswith('\\\\?\\'):
            out_params.report_folder_base = out_params.report_folder_base[4:]
        if input_path.startswith('\\\\?\\'):
            input_path = input_path[4:]
    report.generate_report(out_params.report_folder_base, run_time_secs, run_time_HMS, extracttype, input_path)
    logfunc('Report generation Completed.')
    logfunc('')
    logfunc(f'Report location: {out_params.report_folder_base}')
    return True

if __name__ == '__main__':
    main()
    