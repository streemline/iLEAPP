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

def get_biomeNotificationsPub(files_found, report_folder, seeker, wrap_text):

    typess = {'1': {'type': 'str', 'name': ''}, '2': {'type': 'double', 'name': ''}, '3': {'type': 'int', 'name': ''}, '4': {'type': 'str', 'name': ''}, '5': {'type': 'str', 'name': ''}, '8': {'type': 'str', 'name': ''}, '9': {'type': 'str', 'name': ''}, '11': {'type': 'int', 'name': ''}, '12': {'type': 'str', 'name': ''}, '14': {'type': 'str', 'name': ''}, '16': {'type': 'int', 'name': ''}}

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
                protostuff, types = blackboxprotobuf.decode_message(protostuff,typess)
                #print(protostuff)

                timestart = (timestampsconv(protostuff['2']))
                bundleid = (protostuff['14'])
                data1 = (protostuff.get('8',''))
                data2 = (protostuff.get('9',''))
                data3 = (protostuff.get('12',''))
                data4 = (protostuff.get('15',''))
                data5 = (protostuff.get('5',''))
                if data4 != '':
                    data4 = data4.decode()
                data = (protostuff.get('1',''))

                data_list.append((timestart, bundleid, data1, data2, data3, data4, data5, data))

            modresult = (sizeofnotificaton % 8)
            resultante =  8 - modresult

            if modresult != 0:
                ab.read(resultante)
        if data_list:

            description = ''
            report = ArtifactHtmlReport('Biome Notifications Public')
            report.start_artifact_report(report_folder, f'Biome Notifications Public - {filename}', description)
            report.add_script()
            data_headers = ('Time Start','Bundle ID','Field 1','Field 2','Field 3','Field 4','Field 5','Field 6')
            report.write_artifact_data_table(data_headers, data_list, file_found)
            report.end_artifact_report()

            tsvname = f'Biome Notifications Public - {filename}'
            tsv(report_folder, data_headers, data_list, tsvname) # TODO: _csv.Error: need to escape, but no escapechar set

            tlactivity = f'Biome Notifications Public - {filename}'
            timeline(report_folder, tlactivity, data_list, data_headers)

        else:
            logfunc('No data available for Biome Notifications Public')
    

__artifacts__ = {
    "biomeNotificationsPub": (
        "Biome",
        ('*/biome/streams/public/Notification/local/*'),
        get_biomeNotificationsPub)
}