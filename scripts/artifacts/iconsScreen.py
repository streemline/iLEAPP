import os
import plistlib
import sqlite3
import scripts.artifacts.artGlobals #use to get iOS version -> iOSversion = scripts.artifacts.artGlobals.versionf
from packaging import version #use to search per version number


from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, logdevinfo, is_platform_windows 

def get_iconsScreen(files_found, report_folder, seeker, wrap_text):
    iOSversion = scripts.artifacts.artGlobals.versionf
    if version.parse(iOSversion) >= version.parse("14"):
        logfunc(f'iOS Screen artifact not compatible with iOS {iOSversion}')
        return

    data_list = []
    data_pre_list = []
    file_found = str(files_found[0])
    with open(file_found, "rb") as fp:
        plist = plistlib.load(fp)
        for key, val in plist.items():
            if key == "buttonBar":
                bbar = val
            elif key == "iconLists":
                icon = val

        for x in range(len(icon)):
            page = icon[x]
            htmlstring = "<table><tr>"
            htmlstring = f'{htmlstring}<td colspan="4"> Icons screen #{x}</td>'
            for y in range(len(page)):
                rows = page[y]
                if (y == 0) or (y % 4 == 0):
                    htmlstring = f"{htmlstring}</tr><tr>"

                if isinstance(rows, dict):
                    var = rows
                    foldername = var['displayName'] # TODO throws an error if key not found.
                    rows = (f'Folder: {foldername}')
                    bundlesinfolder = var['iconLists'][0]
                    for items in bundlesinfolder:
                        rows = f'{rows}<br>{items}'

                htmlstring = f"{htmlstring}<td width = 25%>{rows}</td>"
            htmlstring = f"{htmlstring}</tr></table>"
            data_list.append((htmlstring,))

        htmlstring = ''
        htmlstring = '<table><tr> <td colspan="4"> Icons bottom bar</td></tr><tr>'
        for x in range(len(bbar)):
            htmlstring = f"{htmlstring}<td width = 25%>{bbar[x]}</td>"
        htmlstring = f"{htmlstring}</tr></table>"
        data_list.append((htmlstring,))

        logfunc(f"Screens: {len(icon)}")

        report = ArtifactHtmlReport('Apps per screen')
        report.start_artifact_report(report_folder, 'Apps per screen')
        report.add_script()
        data_headers = ('Apps per Screens', )
        report.write_artifact_data_table(data_headers, data_list, file_found, html_escape=False)
        report.end_artifact_report()
     
__artifacts__ = {
    "iconsScreen": (
        "iOS Screens",
        ('**/SpringBoard/IconState.plist'),
        get_iconsScreen)
}