import glob
import os
import nska_deserialize as nd
import sqlite3
import datetime

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, timeline, is_platform_windows, open_sqlite_db_readonly


def get_filesAppsm(files_found, report_folder, seeker, wrap_text):
    for file_found in files_found:
        file_found = str(file_found)

        if file_found.endswith('smartfolders.db'):
            break

    db = open_sqlite_db_readonly(file_found)
    cursor = db.cursor()
    cursor.execute('''
    SELECT * 
    FROM
    FILENAMES
    ''')

    all_rows = cursor.fetchall()
    usageentries = len(all_rows)
    data_list = []
    if usageentries > 0:

        description = 'Files App - Files stored in the "On my iPad" area.'
        tsvname = 'Files App - Filenames'
        tlactivity = 'Files App - Filenames'
        for row in all_rows:
            
            with open(os.path.join(report_folder, f'{row[2]}.bplist'), "wb") as output_file:
                output_file.write(row[1])
            creationdate = contentmodificationdate = userinfo = childitemcount = flags = ''

            with open(os.path.join(report_folder, f'{row[2]}.bplist'), "rb") as f:
                deserialized_plist = nd.deserialize_plist(f)
            for x, y in deserialized_plist.items():
                if x == '_childItemCount':
                    childitemcount = y
                elif x == '_contentModificationDate':
                    contentmodificationdate = y
                elif x == '_creationDate':
                    creationdate = y
                elif x == '_flags':
                    flags = y
                elif x == '_userInfo':
                    userinfo = y
            lasthitdate = datetime.datetime.fromtimestamp(row[3])

            data_list.append((lasthitdate, row[0], row[2],row[4], creationdate, contentmodificationdate, userinfo, childitemcount, flags))

            report = ArtifactHtmlReport('Files App - Filenames')
            report.start_artifact_report(report_folder, 'Files App - Filenames', description)
            report.add_script()
            data_headers = ('Last Hit Date','Folder ID','Filename','Frequency at Las Hit Date','Creation Date','Modification Date','User Info','Child Item Count','Flags' )
            report.write_artifact_data_table(data_headers, data_list, file_found)
            report.end_artifact_report()

            tsv(report_folder, data_headers, data_list, tsvname)

            timeline(report_folder, tlactivity, data_list, data_headers)
    else:
        logfunc('No Files App - Filenames data available')

    db.close()
    
__artifacts__ = {
    "filesAppsm": (
        "Files App",
        ('*private/var/mobile/Containers/Shared/AppGroup/*/smartfolders.db*'),
        get_filesAppsm)
}