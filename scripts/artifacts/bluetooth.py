import plistlib
import datetime

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, timeline, is_platform_windows, open_sqlite_db_readonly

def get_bluetooth(files_found, report_folder, seeker, wrap_text):
    for file_found in files_found:
        file_found = str(file_found)
        if file_found.endswith('com.apple.MobileBluetooth.ledevices.other.db'): # regex '**/Library/Database/com.apple.MobileBluetooth.ledevices.other.db'
            get_bluetoothOther(file_found, report_folder, seeker, wrap_text)
        elif file_found.endswith('com.apple.MobileBluetooth.ledevices.paired.db'): # regex '**/com.apple.MobileBluetooth.ledevices.paired.db'
            get_bluetoothPaired(file_found, report_folder, seeker, wrap_text)
        elif file_found.endswith('com.apple.MobileBluetooth.devices.plist'): # regex '**/com.apple.MobileBluetooth.devices.plist'
            get_bluetoothPairedReg(file_found, report_folder, seeker, wrap_text)

def get_bluetoothOther(file_found, report_folder, seeker, wrap_text):
    db = open_sqlite_db_readonly(file_found)
    cursor = db.cursor()

    cursor.execute(
    """
    SELECT
    Name,
    Address,
    LastSeenTime,
    Uuid
    FROM
    OtherDevices
    order by Name desc
    """)

    all_rows = cursor.fetchall()
    usageentries = len(all_rows)
    data_list = []
    if usageentries > 0:
        data_list.extend((row[0], row[1], row[3]) for row in all_rows)
        description = ''
        report = ArtifactHtmlReport('Bluetooth Other LE')
        report.start_artifact_report(report_folder, 'Other LE', description)
        report.add_script()
        data_headers = ('Name','Address','UUID')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()

        tsvname = 'Bluetooth Other LE'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc('No data available for Bluetooth Other')

    db.close()

def get_bluetoothPaired(file_found, report_folder, seeker, wrap_text):
    db = open_sqlite_db_readonly(file_found)
    cursor = db.cursor()

    cursor.execute("""
    select 
    Uuid,
    Name,
    NameOrigin,
    Address,
    ResolvedAddress,
    LastSeenTime,
    LastConnectionTime
    from 
    PairedDevices
    """)

    all_rows = cursor.fetchall()
    usageentries = len(all_rows)
    data_list = []
    if usageentries > 0:
        data_list.extend(
            (row[0], row[1], row[2], row[3], row[4], row[6])
            for row in all_rows
        )

        description = ''
        report = ArtifactHtmlReport('Bluetooth Paired LE')
        report.start_artifact_report(report_folder, 'Paired LE', description)
        report.add_script()
        data_headers = ('UUID','Name','Name Origin','Address','Resolved Address','Last Connection Time')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()

        tsvname = 'Bluetooth Paired LE'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc('No data available for Bluetooth Paired LE')

    db.close()

def get_bluetoothPairedReg(file_found, report_folder, seeker, wrap_text):
    with open(file_found, 'rb') as f:
        plist = plistlib.load(f)
        #print(plist)
    if len(plist) > 0:
        data_list = []
        for x in plist.items():
            macaddress = x[0]
            #print(x[1])
            if 'LastSeenTime' in x[1]:
                lastseen = x[1]['LastSeenTime']
                lastseen = (datetime.datetime.fromtimestamp(int(lastseen)).strftime('%Y-%m-%d %H:%M:%S'))
            else:
                lastseen = ''
            usernkey = x[1]['UserNameKey'] if 'UserNameKey' in x[1] else ''
            nameu = x[1]['Name'] if 'Name' in x[1] else ''
            deviceid = x[1]['DeviceIdProduct'] if 'DeviceIdProduct' in x[1] else ''
            defname = x[1]['DefaultName'] if 'DefaultName' in x[1] else ''
            data_list.append((lastseen, macaddress, usernkey, nameu, deviceid, defname))

        description = ''
        report = ArtifactHtmlReport('Bluetooth Paired')
        report.start_artifact_report(report_folder, 'Paired', description)
        report.add_script()
        data_headers = ('Last Seen Time','MAC Address','Name Key','Name','Device Product ID','Default Name' )
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()

        tsvname = 'Bluetooth Paired'
        tsv(report_folder, data_headers, data_list, tsvname)

        tlactivity = 'Bluetooth Paired'
        timeline(report_folder, tlactivity, data_list, data_headers)
    else:
        logfunc('No Bluetooth paired devices')

__artifacts__ = {
    "bluetooth": (
        "Bluetooth",
        ('**/com.apple.MobileBluetooth.*'),
        get_bluetooth)
}