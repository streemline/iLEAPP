import os
import struct
import blackboxprotobuf
from datetime import datetime
from time import mktime
from io import StringIO
from io import BytesIO
from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, timeline, is_platform_windows, open_sqlite_db_readonly

def utf8_in_extended_ascii(input_string, *, raise_on_unexpected=False):
    """Returns a tuple of bool (whether mis-encoded utf-8 is present) and str (the converted string)"""
    output = []  # individual characters, join at the end
    is_in_multibyte = False  # True if we're currently inside a utf-8 multibyte character
    multibytes_expected = 0
    multibyte_buffer = []
    mis_encoded_utf8_present = False

    def handle_bad_data(index, character):
        if not raise_on_unexpected: # not raising, so we dump the buffer into output and append this character
            output.extend(multibyte_buffer)
            multibyte_buffer.clear()
            output.append(character)
            nonlocal is_in_multibyte
            is_in_multibyte = False
            nonlocal multibytes_expected
            multibytes_expected = 0
        else:
            raise ValueError(f"Expected multibyte continuation at index: {index}")

    for idx, c in enumerate(input_string):
        code_point = ord(c)
        if code_point <= 0x7f or code_point > 0xf4:  # ASCII Range data or higher than you get for mis-encoded utf-8:
            if not is_in_multibyte:
                output.append(c)  # not in a multibyte, valid ascii-range data, so we append
            else:
                handle_bad_data(idx, c)
        else:  # potentially utf-8
            if (code_point & 0xc0) == 0x80:  # continuation byte
                if is_in_multibyte:
                    multibyte_buffer.append(c)
                else:
                    handle_bad_data(idx, c)
            else:  # start-byte
                if not is_in_multibyte:
                    assert multibytes_expected == 0
                    assert not multibyte_buffer
                    while (code_point & 0x80) != 0:
                        multibytes_expected += 1
                        code_point <<= 1
                    multibyte_buffer.append(c)
                    is_in_multibyte = True
                else:
                    handle_bad_data(idx, c)

        if is_in_multibyte and len(multibyte_buffer) == multibytes_expected:  # output utf-8 character if complete
            utf_8_character = bytes(ord(x) for x in multibyte_buffer).decode("utf-8")
            output.append(utf_8_character)
            multibyte_buffer.clear()
            is_in_multibyte = False
            multibytes_expected = 0
            mis_encoded_utf8_present = True

    if multibyte_buffer:  # if we have left-over data
        handle_bad_data(len(input_string), "")

    return mis_encoded_utf8_present, "".join(output)

def timestampsconv(webkittime):
    unix_timestamp = webkittime + 978307200
    return datetime.utcfromtimestamp(unix_timestamp)

def get_biomeAppinstall(files_found, report_folder, seeker, wrap_text):

    typess = {'1': {'type': 'message', 'message_typedef': {'1': {'type': 'str', 'name': ''}, '2': {'type': 'message', 'message_typedef': {'1': {'type': 'int', 'name': ''}, '2': {'type': 'int', 'name': ''}}, 'name': ''}}, 'name': ''}, '2': {'type': 'double', 'name': ''}, '3': {'type': 'double', 'name': ''}, '4': {'type': 'message', 'message_typedef': {'1': {'type': 'message', 'message_typedef': {'1': {'type': 'int', 'name': ''}, '2': {'type': 'int', 'name': ''}}, 'name': ''}, '3': {'type': 'str', 'name': ''}}, 'name': ''}, '5': {'type': 'str', 'name': ''}, '7': {'type': 'message', 'message_typedef': {'1': {'type': 'message', 'message_typedef': {}, 'name': ''}, '2': {'type': 'message', 'message_typedef': {'1': {'type': 'message', 'message_typedef': {'1': {'type': 'int', 'name': ''}, '2': {'type': 'int', 'name': ''}}, 'name': ''}, '4': {'type': 'int', 'name': ''}, '3': {'type': 'str', 'name': ''}}, 'name': ''}, '3': {'type': 'int', 'name': ''}}, 'name': ''}, '8': {'type': 'double', 'name': ''}, '10': {'type': 'int', 'name': ''}}


    for file_found in files_found:
        file_found = str(file_found)
        filename = os.path.basename(file_found)
        if filename.startswith('.'):
            continue
        if not os.path.isfile(file_found):
            continue

        if 'tombstone' in file_found:
            continue
        with open(file_found, 'rb') as file:
            data = file.read()

        data_list = []
        headerloc = data.index(b'SEGB')
        #print(headerloc)

        b = data
        ab = BytesIO(b)
        ab.seek(headerloc)
        ab.read(4) #Main header
        #print('---- Start of Notifications ----')

        while True:
            #print('----')
            sizeofnotificatoninhex = (ab.read(4))
            try:
                sizeofnotificaton = (struct.unpack_from("<i",sizeofnotificatoninhex)[0])
            except:
                break
            if sizeofnotificaton == 0:
                break

            ignore1 = ab.read(28)

            protostuff = ab.read(sizeofnotificaton)
            checkforempty = BytesIO(protostuff)
            check = checkforempty.read(1)
            if check != b'\x00':
                protostuff, types = blackboxprotobuf.decode_message(protostuff, typess)

                activity = (protostuff['1']['1'])
                timestart = (timestampsconv(protostuff['2']))
                timeend = (timestampsconv(protostuff['3']))

                bundleid = (protostuff['4']['3'])
                actionguid = (protostuff['5'])
                appinfo1 = appinfo2 = ''
                if protostuff.get('7', '') == '':
                    bundleinfo = ''

                elif isinstance(protostuff['7'], list):
                    appinfo1 = (protostuff['7'][0]['2'].get('3', ''))
                    bundleinfo = (protostuff['7'][1]['2'].get('3', ''))
                    appinfo2 = (protostuff['7'][2]['2'].get('3', ''))
                else:
                    bundleinfo = ''
                timewrite = (timestampsconv(protostuff['8']))

                data_list.append((timestart, timeend, timewrite, activity, bundleid, bundleinfo, appinfo1, appinfo2, actionguid ))

            modresult = (sizeofnotificaton % 8)
            resultante =  8 - modresult

            if modresult != 0:
                ab.read(resultante)

        if data_list:

            description = ''
            report = ArtifactHtmlReport('Biome AppInstall')
            report.start_artifact_report(report_folder, f'Biome AppInstall - {filename}', description)
            report.add_script()
            data_headers = ('Time Start','Time End','Time Write','Activity','Bundle ID','Bundle Info', 'App Info', 'App Info', 'Action GUID')
            report.write_artifact_data_table(data_headers, data_list, file_found)
            report.end_artifact_report()

            tsvname = f'Biome AppInstall - {filename}'
            tsv(report_folder, data_headers, data_list, tsvname) # TODO: _csv.Error: need to escape, but no escapechar set

            tlactivity = f'Biome AppInstall - {filename}'
            timeline(report_folder, tlactivity, data_list, data_headers)

        else:
            logfunc('No data available for Biome AppInstall')
    

__artifacts__ = {
    "biomeAppinstall": (
        "Biome",
        ('*/Biome/streams/restricted/_DKEvent.App.Install/local/*'),
        get_biomeAppinstall)
}