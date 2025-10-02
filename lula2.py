#!/usr/bin/env python

""" This a script for process LiveU logs from 4.0 or later devices. """

import subprocess
import os
import sys
from sys import exit
import glob
from datetime import datetime
import shutil
import argparse
import functools

try:
    import regex as re
except ImportError:
    print("Could not find the module regex.  If you are using pip, install it with pip install regex")

VERSION = "4.2"

try:
    from pytz import timezone
except ImportError:
    print("Couldn't find the pytz module. This is required for lula2.\nOn linux, you might install this via sudo apt-get install python-tz.\nIf using pip, install it with sudo pip install pytz")
    exit(6)

try:
    from dateutil.parser import parse
except ImportError:
    print("Couldn't find the python-dateutil module. This is required for lula2.\nOn linux, you might install this via sudo apt-get install python-dateutil\nIf using pip, install it with sudo pip install python-dateutil")
    exit(6)

# Color

CRED = '\033[91m'
CGREEN = '\033[92m'
CYELLOW = '\033[93m'
CBLUE = '\033[94m'
CVIOLET = '\033[95m'
CBLINK = '\033[5m'
CEND = '\033[0m'

def cmp(a, b): return (a > b) - (a < b)

class ShellOut(object):
    @classmethod
    def ex(cls, command):
        rvalue = ''
        worked = True
        try:
            rvalue = subprocess.check_output(command, shell=True)
        except subprocess.CalledProcessError as e:
            rvalue = 'ex failed with: ' + str(e.returncode) + ': ' + e.output.decode('utf-8')
            worked = False
        return (rvalue, worked)

class DateRange(object):
    def __init__(self, start=None, end=None):
        self.includes_start = False
        self.includes_end = False
        self.start = None
        self.end = None
        if start is not None:
            try:
                self.start = parse(start)
            except ValueError:
                print("Unable to parse your begin string as a datetime")
                exit(20)
            self.includes_start = True
        if end is not None:
            try:
                self.end = parse(end)
            except ValueError:
                print("Unable to parse your end string as a datetime")
                exit(20)
            self.includes_end = True

    def existIn(self, date):
        to_return = True
        if date is None:
            to_return = False
        else:

            # print("Checking {0!s} against {1!s} and {2!s} when includes_start is {3!s} and includes_end is {4!s}".format(date,self.start,self.end,self.includes_start,self.includes_end))
            if self.includes_start and self.start > date:
                to_return = False
            if self.includes_end and self.end < date:
                to_return = False

        return to_return

class FfmpegLogLine(object):
    def __init__(self, raw_line, timezone):
        self.raw = raw_line.decode("utf-8")
        self.timezone = timezone

class ICCID(object):
    def __init__(self, iccid):
        self.sim_provider = "Unknown"
        if iccid:
            iccid_prefix_5 = iccid[0:5]
            iccid_prefix_6 = iccid[0:6]
            if iccid_prefix_6 == '898523':
                self.sim_provider = "Webbing"
            elif iccid_prefix_6 == '893108':
                self.sim_provider = 'RiteSIM'
            elif iccid_prefix_5 == '89011':
                self.sim_provider = 'AT&T Roaming'


class LogLine(object):
    def __init__(self, raw_line, timezone):
        self.raw = raw_line.decode("utf-8")
        self.timezone = timezone
        self.datetime = self._getDatetimeFromLine(self.raw)
        self.message = self.raw[33:]

    def _getDatetime(self, str_timestamp):
        tz = timezone(self.timezone)
        parsed_date = None
        try:
            parsed_date = parse(str_timestamp).astimezone(tz)
        except (ValueError, TypeError):
            pass

        return parsed_date

    def _getDatetimeFromLine(self, line):
        return self._getDatetime(line.split()[0])

class ConnectivitySummary(object):
    connections = {}
    on = False
    _local = None

    def __init__(self):
        pass

    @classmethod
    def instance(cls):
        if cls._local is None:
            cls._local = cls()
        return cls._local

    def addLogLine(self, modem, line, message):
        if modem not in self.connections:
            self.connections[modem] = []
        self.connections[modem].append([line, message])

    def outputReport(self):
        for modem in sorted(self.connections.keys()):
            print(modem + ':')
            for line_tuple in self.connections[modem]:
                print("{0!s}: {1!s}".format(line_tuple[0].datetime, line_tuple[1]))
            print('')
            print('')



class ModemSummary(object):
    modems = {}
    _local = None

    def __init__(self):
        pass

    @classmethod
    def instance(cls):

        if cls._local is None:
            cls._local = cls()

        return cls._local

    def prepareModem(self, modem_n):
        if modem_n not in self.modems:
            self.modems[modem_n] = Modem(modem_n)

    def parseModem(self, pattern, line):
        match = re.search(pattern, line.raw)
        if match:
            modem_n = match.group(1)
            self.prepareModem(modem_n)

            self.modems[modem_n].addData(line.datetime, match.group(2), match.group(3), match.group(4), match.group(5), match.group(6), match.group(7))
            return True
        else:
            return False

    def parseLine(self, line):
        # INFO:Modem Statistics for modem 8: potentialBW 2931kbps, 0% loss, 43ms up extrapolated delay, 39ms shortest round trip delay, 43ms smooth round trip delay, 40ms minimum smooth round trip delay
        # INFO:Modem Statistics for modem 0: potentialBW 267kbps, loss (0%), extrapolated smooth upstream delay (579ms), shortest round trip delay (1537ms), extrapolated smooth round trip delay (1623ms), minimum smooth round trip delay
        pattern = r"Modem Statistics for modem (\d+): potentialBW (\d+)k?bps, (\d+)\% loss, (\d+)ms up extrapolated delay, (\d+)ms shortest round trip delay, (\d+)ms smooth round trip delay, (\d+)ms minimum smooth round trip delay"
        if not self.parseModem(pattern, line):
            pattern = r"Modem Statistics for modem (\d+): potentialBW (\d+)k?bps, loss \((\d+)\%\), extrapolated smooth upstream delay \((\d+)ms\), shortest round trip delay \((\d+)ms\), extrapolated smooth round trip delay \((\d+)ms\), minimum smooth round trip delay \((\d+)ms\)"
            self.parseModem(pattern, line)

    def output(self):
        for modem in sorted(self.modems):
            self.modems[modem].output()
            print

class HighLowAverage(object):
    def __init__(self, lb):
        self.label = lb
        self.lowest_value = None
        self.highest_value = 0
        self.total_samples = 0
        self.average_value = 0
        self.running_sum = 0
        self.datetime_of_high = None
        self.datetime_of_low = None

    def append(self, value, datetime):
        value = int(value)
        self.total_samples = self.total_samples + 1
        self.running_sum = self.running_sum + value

        if self.lowest_value is None:
            self.lowest_value = value
            self.datetime_of_low = datetime

        if value < self.lowest_value:
            self.lowest_value = value
            self.datetime_of_low = datetime

        if value > self.highest_value:
            self.highest_value = value
            self.datetime_of_high = datetime

    def average(self):
        return self.running_sum / float(self.total_samples)

class Modem(object):
    def __init__(self, modem_n):
        self.modem_number = modem_n
        self.potential_bw = HighLowAverage('Potential Bandwidth')
        self.percent_loss = HighLowAverage('Percent Loss')
        self.extrapolated_delay = HighLowAverage('Extrapolated Delay')
        self.shortest_round_trip = HighLowAverage('Shortest Round Trip')
        self.smooth_round_trip = HighLowAverage('Smooth Round Trip')
        self.minimum_smooth_round_trip = HighLowAverage('Minimum Smooth Round Trip')

    def addData(self, datetime, potential_bw, percent_loss, extrapolated_delay, shortest_round_trip, smooth_round_trip, minimum_smooth_round_trip):
        self.potential_bw.append(potential_bw, datetime)
        self.percent_loss.append(percent_loss, datetime)
        self.extrapolated_delay.append(extrapolated_delay, datetime)
        self.shortest_round_trip.append(shortest_round_trip, datetime)
        self.smooth_round_trip.append(smooth_round_trip, datetime)
        self.minimum_smooth_round_trip.append(minimum_smooth_round_trip, datetime)

    def output(self):
        print("Modem {0!s}".format(self.modem_number))
        print("\tPotential Bandwidth (kbps) (L/H/A): {0!s} / {1!s} / {2!s}".format(self.potential_bw.lowest_value, self.potential_bw.highest_value, self.potential_bw.average()))
        print("\t\tTime of L: {0!s}".format(self.potential_bw.datetime_of_low))
        print("\t\tTime of H: {0!s}".format(self.potential_bw.datetime_of_high))
        print("\tPercent Loss (L/H/A): {0!s} / {1!s} / {2!s}".format(self.percent_loss.lowest_value, self.percent_loss.highest_value, self.percent_loss.average()))
        print("\t\tTime of L: {0!s}".format(self.percent_loss.datetime_of_low))
        print("\t\tTime of H: {0!s}".format(self.percent_loss.datetime_of_high))
        print("\tExtrapolated Up Delay (ms) (L/H/A): {0!s} / {1!s} / {2!s}".format(self.extrapolated_delay.lowest_value, self.extrapolated_delay.highest_value, self.extrapolated_delay.average()))
        print("\t\tTime of L: {0!s}".format(self.extrapolated_delay.datetime_of_low))
        print("\t\tTime of H: {0!s}".format(self.extrapolated_delay.datetime_of_high))
        print("\tShortest Round Trip Delay (ms) (L/H/A): {0!s} / {1!s} / {2!s}".format(self.shortest_round_trip.lowest_value, self.shortest_round_trip.highest_value, self.shortest_round_trip.average()))
        print("\t\tTime of L: {0!s}".format(self.shortest_round_trip.datetime_of_low))
        print("\t\tTime of H: {0!s}".format(self.shortest_round_trip.datetime_of_high))
        print("\tSmooth Round Trip (ms) (L/H/A): {0!s} / {1!s} / {2!s}".format(self.smooth_round_trip.lowest_value, self.smooth_round_trip.highest_value, self.smooth_round_trip.average()))
        print("\t\tTime of L: {0!s}".format(self.smooth_round_trip.datetime_of_low))
        print("\t\tTime of H: {0!s}".format(self.smooth_round_trip.datetime_of_high))
        print("\tMinimum Smooth Round Trip (ms) (L/H/A): {0!s} / {1!s} / {2!s}".format(self.minimum_smooth_round_trip.lowest_value, self.minimum_smooth_round_trip.highest_value, self.minimum_smooth_round_trip.average()))
        print("\t\tTime of L: {0!s}".format(self.minimum_smooth_round_trip.datetime_of_low))
        print("\t\tTime of H: {0!s}".format(self.minimum_smooth_round_trip.datetime_of_high))

class StreamSession(object):
    def __init__(self, start, end, lid):
        self.found_start = False
        self.session_id_present = False
        self.start = None
        if start is not None:
            self.found_start = True
            self.start = start

        self.found_end = False
        if end is not None:
            self.end = end
            self.found_end = True

        if lid is not None:
            self.sid = lid
            self.session_id_present = True

    def duration(self):
        if self.found_start and self.found_end:
            return self.end - self.start
        else:
            return "Unknown"

    def completeSession(self):
        return self.found_start and self.found_end

    def asString(self):
        if self.completeSession():
            if self.session_id_present:
                return "Complete (session id: {3!s}): -b '{0!s}' -e '{1!s}', {2!s}".format(self.start, self.end, self.duration(), self.sid)
            else:
                return "Complete (no session id found): -b '{0!s}' -e '{1!s}', {2!s}".format(self.start, self.end, self.duration())
        elif self.found_start:
            if self.session_id_present:
                return "Start Only (session id: {1!s}: {0!s}".format(self.start, self.sid)
            else:
                return "Start Only (no session id found): {0!s}".format(self.start)
        else:
            if self.session_id_present:
                return "End Only (session id: {1!s}):   {0!s}".format(self.end, self.sid)
            else:
                return "End Only (no session id found):   {0!s}".format(self.end)

# TODO: make a modem tracker object here that will organize modem lines by the USB port number

class SessionTracker(object):
    _local = None

    def __init__(self):
        pass

    @classmethod
    def instance(cls):
        if cls._local is None:
            cls._local = cls()

        return cls._local

    def __init__(self):
        self.in_session = False
        self.sessions = []
        self.current_start = None
        self.current_session_id = None
        self.sid = None

    def logSessionId(self, lid):
        self.current_session_id = lid

    def logStart(self, dt):
        if not self.in_session:
            self.in_session = True
            self.current_start = dt
        else:
            # got a second start when never receiced an end
            self.in_session = True
            self.sessions.append(StreamSession(self.current_start, None, self.current_session_id))
            self.current_start = dt

    def logEnd(self, dt):
        if self.in_session:
            self.in_session = False
            self.sessions.append(StreamSession(self.current_start, dt, self.current_session_id))
            self.current_start = None
            self.current_session_id = None
        else:
            # Got an end when we never got a start
            self.in_session = False
            self.sessions.append(StreamSession(None, dt, self.current_session_id))
            self.current_start = None
            self.current_session_id = None

    def close(self):
        if self.in_session:
            self.sessions.append(StreamSession(self.current_start, None, self.current_session_id))
            self.in_session = False
            self.current_start = None
            self.current_session_id = None

    def outputAll(self):
        print('')
        for session in self.sessions:
            print(session.asString())

class FfmpegLineProcessors(object):
    def __init__(self):
        self.timezone = 'US/Eastern'
        self.daterange = DateRange()
        self.stored_last_timestamp = ''
        self.parse_type = ''
        self.remove_lines = []
        self.remove_lines.append(self.findUpdateLine)
        self.remove_lines.append(self.findLUSepLine)
        self.remove_lines.append(self.findSdpReadLine)
        self.remove_lines.append(self.findMessageRepeat)
        self.remove_lines.append(self.findGraphLine)
        self.remove_lines.append(self.findDTSLine)
        self.remove_lines.append(self.findHelpLine)
        self.remove_lines.append(self.findFfmpeg1stLine)
        self.remove_lines.append(self.findFfmpegBuildLine)
        self.remove_lines.append(self.findFfmpegConfigureLine)
        self.remove_lines.append(self.findLibraryVersionLine)

        self.ffmpeg_semantic_lines = []
        self.ffmpeg_semantic_lines.append(self.findFFmpegVideoFound)
        self.ffmpeg_semantic_lines.append(self.findUnknownError)
        self.ffmpeg_semantic_lines.append(self.findSocketUnavailable)
        self.ffmpeg_semantic_lines.append(self.findFailedToReadHeader)
        self.ffmpeg_semantic_lines.append(self.findSendError32)



    def findHeaderMarker(self, line, filename):
        pattern = r"(\d\d\d\d\-\d\d\-\d\d [^\s]*) ffmpeg"
        match = re.search(pattern, line.raw)
        if match:
            # print(line.raw)
            print("")
            this_timestamp = self._getDatetime(match.group(1))
            self.stored_last_timestamp = this_timestamp
            print("{0!s}: Start of ffmpeg command (True date: {1!s})".format(this_timestamp,match.group(1)))
            return True
        return False

    def findArgs(self, line, filename):
        pattern = r"ARGS: \("
        match = re.search(pattern, line.raw)
        if match:
            # print(line.raw)
            print(line.raw)
            return True
        return False


    def _getDatetime(self, str_timestamp_no_zone):
        tz = timezone(self.timezone)
        parsed_date = None
        try:
            parsed_date = parse(str_timestamp_no_zone + "-00:00").astimezone(tz)
        except (ValueError, TypeError):
            pass

        return parsed_date

    def _findPattern(self, pattern, line, filename):
        match = re.search(pattern, line.raw)
        if match:
            # print(match.group(0))
            return True
        return False

    def findUpdateLine(self, line, filename):
        # frame=389790 fps= 50 q=-1.0 size= 5804743kB time=02:10:04.60 bitrate=6092.9kbits/s speed=   1x
        pattern = r"frame=\s*\d* fps=\s*[\d\.]* q=[^\s]* size=\s*[^\s]* time="
        return self._findPattern(pattern, line, filename)

    def findLUSepLine(self, line, filename):
        # ************************************************************************************************************************
        if line.raw == "************************************************************************************************************************":
            return True
        return False

    def findSdpReadLine(self, line, filename):
        #might want to do something with these later
#         [sdp @ 0x1ed0180] RTP: missed 22 packets
# [sdp @ 0x1ed0180] max delay reached. need to consume packet
        pattern = r"\[sdp @ 0x[^\]]+\]"
        return self._findPattern(pattern, line, filename)

    def findMessageRepeat(self, line, filename):
        pattern = r"\s+Last message repeated"
        return self._findPattern(pattern, line, filename)

    def findGraphLine(self, line, filename):
        pattern = r"\[graph_0_in_0_1 @ "
        return self._findPattern(pattern, line, filename)

    def findDTSLine(self, line, filename):
        pattern = r"\[flv @ [^\]]*\] Non-monotonous DTS in output stream "
        return self._findPattern(pattern, line, filename)

    def findHelpLine(self, line, filename):
        pattern = r"Press \[q\] to stop, \[\?\] for help"
        return self._findPattern(pattern, line, filename)

    def findFfmpeg1stLine(self, line, filename):
        pattern = r"ffmpeg version [^\s]+ Copyright (c) [^\s]+ the FFmpeg developers"
        return self._findPattern(pattern, line, filename)

    def findFfmpegBuildLine(self, line, filename):
        pattern =  r"built with gcc [^\s]+ ([^\s]+) [^\s]+"
        return self._findPattern(pattern, line, filename)

    def findFfmpegConfigureLine(self, line, filename):
        pattern =   r"configuration:.*--enable-ffmpeg.*"
        return self._findPattern(pattern, line, filename)

    def findLibraryVersionLine(self, line, filename):
        pattern =  r"\s\slib[^\s]+\s+\d+\.\s+\d+\."
        return self._findPattern(pattern, line, filename)

    def findFFmpegVideoFound(self, line, filename):
        pattern = r"Input #0, sdp, from '.+':"
        match = self._findPattern(pattern, line, filename)
        if match:
            self.printFfmpegLine("ffmpeg discovered video and audio and started")

    def findUnknownError(self, line, filename):
        pattern = r"rtmp://([^:]+): Unknown error occurred"
        match = self._findPattern(pattern, line, filename)
        if match:
            self.printFfmpegLine("'Unknown Error' reported")

# 2021-09-01 14:31:11+00:00: RTMPSockBuf_Fill, recv returned -1. GetSockError(): 11 (Resource temporarily unavailable)
# 2021-09-01 14:31:11+00:00: RTMP_ReadPacket, failed to read RTMP packet header

    def findSocketUnavailable(self, line, filename):
        pattern = r"GetSockError\(\): 11 \(Resource temporarily unavailable\)"
        match = self._findPattern(pattern, line, filename)
        if match:
            self.printFfmpegLine("Get socket error resource tempoararily unavailable reported")

    def findFailedToReadHeader(self, line, filename):
        pattern = r"RTMP_ReadPacket, failed to read RTMP packet header"
        match = self._findPattern(pattern, line, filename)
        if match:
            self.printFfmpegLine("failed to read RTMP packet header")

    def findSendError32(self, line, filename):
        pattern = r"RTMP send error 32"
        match = self._findPattern(pattern, line, filename)
        if match:
            self.printFfmpegLine("Server disconnected (RTMP Send Error 32)")



    def printFfmpegLine(self, line):
        print("{0!s}: {1!s}".format(self.stored_last_timestamp, line))

    def process(self, line, filename):
        if self.parse_type == 'ffmpeg':
            self.process_remove(line, filename)
        elif self.parse_type == 'ffmpegv':
            self.process_semantic(line, filename)
        elif self.parse_type == 'ffmpega':
            self.process_all(line, filename)

    def process_semantic(self, line, filename):
        log_line = None
        decoded = False


        try:
            log_line = FfmpegLogLine(line, self.timezone)
            decoded = True
        except UnicodeDecodeError:
            pass

        if decoded:
            if not self.findHeaderMarker(log_line, filename):
                if not self.findArgs(log_line, filename):
                    for processor in self.ffmpeg_semantic_lines:
                        if processor(log_line, filename):
                            break


    def process_remove(self, line, filename):
        # print(line)
        log_line = None
        decoded = False


        try:
            log_line = FfmpegLogLine(line, self.timezone)
            decoded = True
        except UnicodeDecodeError:
            pass

        if decoded:
            if not self.findHeaderMarker(log_line, filename):
                if not self.findArgs(log_line, filename):
                    print_it = True
                    for remove_if in self.remove_lines:
                        if remove_if(log_line, filename):
                            print_it = False
                    if print_it:
                        #print(log_line.raw)
                        self.printFfmpegLine(log_line.raw)

    def process_all(self, line, filename):
        log_line = None
        decoded = False


        try:
            log_line = FfmpegLogLine(line, self.timezone)
            decoded = True
        except UnicodeDecodeError:
            pass

        if decoded:
            if not self.findHeaderMarker(log_line, filename):
                if not self.findArgs(log_line, filename):
                    self.printFfmpegLine(log_line.raw)


# b'************************************************************************************************************************'
# b'2021-06-02 08:41:13 ffmpeg '
# b"ARGS: (['ffmpeg', '-loglevel', 'verbose', '-protocol_whitelist', 'file,udp,rtp', '-y', '-i', '/tmp/sdp_cdn_instance_11_stream_0_0', '-c:v', 'copy', '-b:v', '4000.0k', '-c:a', 'aac', '-b:a', '96k', '-ar', '48000', '-f', 'flv', 'rtmp://groverserver21.bartvstream.com/input1 playpath=input1'],)"
# b'************************************************************************************************************************'



class LineProcessors(object):
    def __init__(self):
        self.timezone = 'US/Eastern'
        self.daterange = DateRange()
        self.parse_type = None
        self.all_processors = []
        self.csv_processors = []
        self.csv_loss_processors = []
        self.csv_loss_db_processors = []
        self.verbose_processors = []
        self.debug_processors = []
        self.id_processors = []
        self.memory_processors = []
        self.modem_grading_processors = []
        self.cpu_processors = []
        self.debug_processors = []
        self.modem_event_processors = []

        self.all_processors.append(self.streamSessionStart)
        self.all_processors.append(self.streamSessionStartSolo)
        self.all_processors.append(self.streamSessionEndSolo)
        self.all_processors.append(self.streamSessionEnd)
        self.all_processors.append(self.eggCrashSystem)
        self.all_processors.append(self.eggCrashSoftware)
        self.all_processors.append(self.eggRestartWarning)
        self.all_processors.append(self.eggRestartError)
        self.all_processors.append(self.videoInputDisconnectError)
        self.all_processors.append(self.sdiInvalidVideoInputWarning)
        self.all_processors.append(self.pantechIn70AssertionError)
        self.all_processors.append(self.streamSessionStartInVersion5)
        self.all_processors.append(self.startSessionType)
        self.all_processors.append(self.cvicGeneration)
        self.all_processors.append(self.deviceSoftwareVersion)
        self.all_processors.append(self.cameraStatusConnectDisconnectCvic)
        self.all_processors.append(self.cameraStatusConnectAvic)
        self.all_processors.append(self.cameraStatusDisconnectAvic)
        self.all_processors.append(self.cameraDisconnectedStatusTimer)
        self.all_processors.append(self.cameraDisconnectedStatusTimerError)
        # self.all_processors.append(self.stopEncoderAndRecorderState) Moved under debug
        # self.all_processors.append(self.startForwardingState) Moved under debug
        # self.all_processors.append(self.sendingFileDone) Moved under debug
        self.all_processors.append(self.profileQueryErrorAfterUpgrade)
        self.all_processors.append(self.rebootRequestFromGuiOrLuc)
        self.all_processors.append(self.rebootRequestFromMedic)
        self.all_processors.append(self.unitSyslogStartup)
        self.all_processors.append(self.unitPowerShutdownRequested)
        # self.all_processors.append(self.i2cBusRecovery) Moved under debug
        self.all_processors.append(self.maxQualityAtLowDelay)
        self.all_processors.append(self.vicType)
        # self.all_processors.append(self.vicSerialNumber) Moved under debug
        # self.all_processors.append(self.vicSoftwareVersionValidation) Moved under debug
        # self.all_processors.append(self.avicSoftwareVersion) Moved under debug
        self.all_processors.append(self.machineModel)
        self.all_processors.append(self.unitStopCommandFromGui)
        self.all_processors.append(self.unitStopCommandFromCentral)
        self.all_processors.append(self.unitStartCommandFromCentral)
        # self.all_processors.append(self.videoInputResolution) removing for now
        self.all_processors.append(self.sdiVideoInputResolution)
        self.all_processors.append(self.hdmiVideoInputResolution)
        self.all_processors.append(self.unitBackfireConnectionError)
        self.all_processors.append(self.ackReciveWarning)
        self.all_processors.append(self.dataReciveInfo)
        self.all_processors.append(self.unitIncomingDataFlowColectorWarning)
        self.all_processors.append(self.unitPresenterLu100ErrorSystem)
        self.all_processors.append(self.unitPresenterLu100ErrorSoftware)
        # self.all_processors.append(self.socketAddressWarningEggAlreadyStarted) Moved under debug
        self.all_processors.append(self.soloFfmpegCrashError)
        self.all_processors.append(self.soloFfmpegCrashErrorVersion7)
        self.all_processors.append(self.multimediaTransformerCrashError)
        self.all_processors.append(self.streamSessionStartServer)
        self.all_processors.append(self.streamSessionEndServer)
        self.all_processors.append(self.serverUpgradeError)
        self.all_processors.append(self.whoIsStreamingToThisChannel)
        self.all_processors.append(self.playFileToSdiSessionStartServer)
        self.all_processors.append(self.playFileToSdiSessionEndServer)
        self.all_processors.append(self.unitStoppingStreamCollectorStopped)
        self.all_processors.append(self.serverCollectorStoppedReceivingData)
        self.all_processors.append(self.serverBackfireConnectionError)
        self.all_processors.append(self.stopStreamCommandFromInfo)
        self.all_processors.append(self.serviceLiveuStart)
        self.all_processors.append(self.gatewayChannelAllocated)
        self.all_processors.append(self.streamSessionStartDataBridge)
        self.all_processors.append(self.streamSessionEndDataBridge)
        self.all_processors.append(self.dataBrdgeCollectorCrashError)
        self.all_processors.append(self.switchingFromVideoToDataBridgeMode)
        self.all_processors.append(self.timeoutWaitingStartStreamingDataBridge)
        self.all_processors.append(self.streamSessionStartDataBridgeMultiPath)
        self.all_processors.append(self.streamSessionEndDataBridgeMultiPath)
        self.all_processors.append(self.streamAtVideoGatewayFailedToStart)
        self.all_processors.append(self.modemconfigurationCorrupted)

        self.csv_processors.append(self.csvBitrateTotal)
        self.csv_processors.append(self.csvBitrateTotalVersion50)
        self.csv_processors.append(self.csvBitrateCongestionTotal)
        self.csv_processors.append(self.csvBitrateStreamSessionStart)
        self.csv_processors.append(self.csvBitrateStreamSessionEnd)

        self.csv_loss_processors.append(self.csvModemBwStatistics)
        self.csv_loss_processors.append(self.csvModemBwStatisticsStreamSessionStart)
        self.csv_loss_processors.append(self.csvModemBwStatisticsStreamSessionEnd)
        self.csv_loss_processors.append(self.csvModemBwStatisticsModemDisconnected)

        self.csv_loss_db_processors.append(self.csvModemBwStatisticsDb)
        self.csv_loss_db_processors.append(self.csvModemBwStatisticsStreamSessionStartDb)
        self.csv_loss_db_processors.append(self.csvModemBwStatisticsStreamSessionEndDb)
        self.csv_loss_db_processors.append(self.csvModemBwStatisticsStreamSessionStartDbGw)
        self.csv_loss_db_processors.append(self.csvModemBwStatisticsStreamSessionEndDbGw)
        self.csv_loss_db_processors.append(self.csvModemBwStatisticsModemDisconnected)

        self.modem_grading_processors.append(self.streamSessionStartInVersion5)
        self.modem_grading_processors.append(self.streamSessionStart)
        self.modem_grading_processors.append(self.streamSessionEnd)
        self.modem_grading_processors.append(self.streamSessionStartServer)
        self.modem_grading_processors.append(self.streamSessionEndServer)
        self.modem_grading_processors.append(self.modemGradingLimitedServiceRttValues)
        self.modem_grading_processors.append(self.modemGradingLimitedService)
        self.modem_grading_processors.append(self.modemGradingLimitedServiceLossValue)
        self.modem_grading_processors.append(self.modemGradingFullServiceRttValues)
        self.modem_grading_processors.append(self.modemGradingFullService)
        self.modem_grading_processors.append(self.modemGradingFullServiceLossValue)

        self.id_processors.append(self.streamingUnitBossId)
        self.id_processors.append(self.streamToChannelBossId)

        self.memory_processors.append(self.memoryStreamSessionStart)
        self.memory_processors.append(self.memoryStreamSessionStartDataBridgeUnit)
        self.memory_processors.append(self.memoryStreamSessionEndDataBridgeUnit)
        self.memory_processors.append(self.memoryStreamSessionStartServer)
        self.memory_processors.append(self.memoryStreamSessionEndServer)
        self.memory_processors.append(self.memoryStreamSessionEnd)
        self.memory_processors.append(self.memoryVicWarning)
        self.memory_processors.append(self.memoryCorecardWarning)
        self.memory_processors.append(self.memoryServerWarning)
        self.memory_processors.append(self.memoryServerInfo)
        self.memory_processors.append(self.memoryVicInfo)
        self.memory_processors.append(self.memoryCorecardInfo)

        self.cpu_processors.append(self.memoryStreamSessionStart)
        self.cpu_processors.append(self.memoryStreamSessionStartDataBridgeUnit)
        self.cpu_processors.append(self.memoryStreamSessionEndDataBridgeUnit)
        self.cpu_processors.append(self.memoryStreamSessionStartServer)
        self.cpu_processors.append(self.memoryStreamSessionEndServer)
        self.cpu_processors.append(self.memoryStreamSessionEnd)
        self.cpu_processors.append(self.cpuVicWarning)
        self.cpu_processors.append(self.cpuVicWarningVersion7)
        self.cpu_processors.append(self.cpuCorecardWarning)
        self.cpu_processors.append(self.cpuCorecardWarningVersion7)
        self.cpu_processors.append(self.cpuServerWarning)
        self.cpu_processors.append(self.cpuServerWarningVersion7)
        self.cpu_processors.append(self.cpuServerInfo)
        self.cpu_processors.append(self.cpuVicInfo)
        self.cpu_processors.append(self.cpuCorecardInfo)

        extra_processors = []
        extra_processors.append(self.unitVideoSkips)
        extra_processors.append(self.unitPacketDroppWarning)
        extra_processors.append(self.unitRtpGapInfo)
        extra_processors.append(self.frameErrorWarningServer)
        extra_processors.append(self.decodingFrameErrorServer)
        extra_processors.append(self.onlineOfflineDuringLiveSession)
        extra_processors.append(self.onlineOfflineDuringStoreAndForwardSession)
        extra_processors.append(self.offlineInIdle)
        # extra_processors.append(self.hubConnectAttemptUnit) Moved under debug
        extra_processors.append(self.connectedToHubUnit)
        # extra_processors.append(self.remoteControlActiveConnectionNumber) Moved under debug
        extra_processors.append(self.connectedToHub)
        extra_processors.append(self.portDisabledByEmi)
        extra_processors.append(self.portResetByEmi)
        extra_processors.append(self.natTableFull)
        extra_processors.append(self.failedToReadRegister)
        # extra_processors.append(self.symanticSesssionId)
        # extra_processors.append(self.hubConnectAttemptServer) Moved under debug
        extra_processors.append(self.connectedToHubServer)
        extra_processors.append(self.onlineOfflineDuringLiveSessionDataBridge)
        extra_processors.append(self.onlineOfflineWhileStartingCollectorDataBridge)
        extra_processors.append(self.dhcpFailedDataBridge)
        extra_processors.append(self.offlineDuringCollectingGwDataBridge)
        extra_processors.append(self.timeoutWaitingForCollectorToStartDataBridge)
        extra_processors.append(self.startCollectorDataBridge)
        extra_processors.append(self.hubConnectionTimeout)
        extra_processors.append(self.hubHubConnectionTimeoutModem)
        # extra_processors.append(self.sdiCableConnectDisconnect)
        # extra_processors.append(self.hdmiCableConnectDisconnect)
        # extra_processors.append(self.softwareStartup) #Removed. Added signalbus start. Moved under debug
        extra_processors.append(self.potentialBandwidthIsZero)
        extra_processors.append(self.interfacesReadyForStreaming)
        extra_processors.append(self.leastCostBondingActivatedForChargeableLinks)
        extra_processors.append(self.leastCostBondingActivatedForFreeLinks)
        extra_processors.append(self.ethernetInterfaceCableDisconnectedRemoved)
        extra_processors.append(self.ethernetInterfaceCableDisconnectedRemovedVersion7)
        extra_processors.append(self.ethernetInterfaceConnected)
        extra_processors.append(self.ethernetInterfaceConnectedVersion7)
        extra_processors.append(self.wifiInterfaceDisconnectedDisabled)
        extra_processors.append(self.wifiInterfaceDisconnectedDisabledVersion7)
        extra_processors.append(self.wifiInterfaceConnected)
        extra_processors.append(self.modemInterfaceDisconnectedDisabled)
        extra_processors.append(self.modemInterfaceRemoved)
        extra_processors.append(self.modemInterfaceRemovedVersion7)
        extra_processors.append(self.modemInterfaceConnected)
        extra_processors.append(self.modemInterfaceConnectedVersion7)
        extra_processors.append(self.modemInterfaceDisconnectedNotReachingInternet)
        extra_processors.append(self.modemInterfaceDisconnectedNotReachingInternetVersion7)
        extra_processors.append(self.modemInterfaceDisconnectedNotReachingInternetAfterThreeRetries)
        extra_processors.append(self.modemInterfaceDisconnectedNotReachingInternetAfterThreeRetriesVersion7)
        extra_processors.append(self.xtenderEthernetConnected)
        extra_processors.append(self.xtenderEthernetConnectedVersion7)
        extra_processors.append(self.xtenderEthernetDisconnected)
        extra_processors.append(self.xtenderEthernetDisconnectedVersion7)
        extra_processors.append(self.ubiquityConnected)
        extra_processors.append(self.ubiquityDisconnected)
        extra_processors.append(self.totalBandwidthLow)
        extra_processors.append(self.videoRtpPacketsOutOfSequenceServer)
        extra_processors.append(self.audioRtpPacketsOutOfSequenceServer)
        extra_processors.append(self.ethernetLinkUpDownUnit)
        extra_processors.append(self.dhcpAttemptDataBridge)
        extra_processors.append(self.dhcpObtainedDataBridge)
        extra_processors.append(self.hubConnectionTimeoutDataBridgeGateway)
        extra_processors.append(self.videoEndToEndDelay)
        extra_processors.append(self.unitTotalBandwidthLimitChange)
        extra_processors.append(self.unitTotalBandwidthLimit)
        extra_processors.append(self.selectedChannelId)
        # extra_processors.append(self.blackMagicCardSoftwareVersion) Moved under debug
        extra_processors.append(self.audioOutputTypeTwoChannels)
        extra_processors.append(self.audioOutputTypeFourChannels)
        extra_processors.append(self.p2mpStreamStart)
        extra_processors.append(self.p2mpStreamStop)
        extra_processors.append(self.p2mpAddingSubscriber)
        extra_processors.append(self.p2mpRemovingSubscriber)
        extra_processors.append(self.p2mpMultimediaDistributerError)
        # extra_processors.append(self.fileTransferSessionComplete) Moved under debug
        extra_processors.append(self.audioCodecResetUnit)
        extra_processors.append(self.transmitQueueTimeout)
        extra_processors.append(self.unitOfflineDuringCollectingSession)
        extra_processors.append(self.unitOnlineDuringCollectingSession)
        extra_processors.append(self.collectorStoppingDueToIdleStateOfTheDevice)
        extra_processors.append(self.bandwidthLimitForModemSetting)
        # extra_processors.append(self.monitorChannelReadiness) Moved under debug
        extra_processors.append(self.destinationIdSettings)

        debuging_processors = []
        debuging_processors.append(self.fileTransferSessionComplete)
        debuging_processors.append(self.vicSerialNumber)
        debuging_processors.append(self.vicSoftwareVersionValidation)
        debuging_processors.append(self.avicSoftwareVersion)
        debuging_processors.append(self.remoteControlActiveConnectionNumber)
        # debuging_processors.append(self.monitorChannelReadiness)
        debuging_processors.append(self.sdiCableConnectDisconnect)
        debuging_processors.append(self.hdmiCableConnectDisconnect)
        # debuging_processors.append(self.i2cBusRecovery)
        debuging_processors.append(self.socketAddressWarningEggAlreadyStarted)
        debuging_processors.append(self.hubConnectAttemptUnit)
        debuging_processors.append(self.hubConnectAttemptServer)
        debuging_processors.append(self.stopEncoderAndRecorderState)
        debuging_processors.append(self.startForwardingState)
        debuging_processors.append(self.sendingFileDone)
        debuging_processors.append(self.detected_videores)
        debuging_processors.append(self.blackMagicCardSoftwareVersion)
        debuging_processors.append(self.peerListInterfacesAdd)
        debuging_processors.append(self.peerListInterfacesRemove)
        debuging_processors.append(self.modemGradingLimitedService)
        debuging_processors.append(self.modemGradingFullService)
        debuging_processors.append(self.shotingModeChange)
        debuging_processors.append(self.switchingHub)
        debuging_processors.append(self.switchingHubVersion7)
        debuging_processors.append(self.symanticSesssionId)

        modem_event_processors = []
        modem_event_processors.append(self.currentOperator)
        modem_event_processors.append(self.linkRedyForStreaming)
        modem_event_processors.append(self.manualOperatorSelect)
        modem_event_processors.append(self.linkLine)
        modem_event_processors.append(self.dhcpLinkLine)
        modem_event_processors.append(self.roamingService)
        modem_event_processors.append(self.linkConnected)
        modem_event_processors.append(self.qmiLink)
        # modem_event_processors.append(self.interfacesReadyForStreaming)


        self.verbose_processors = self.all_processors + extra_processors

        self.debug_processors = self.verbose_processors + debuging_processors

        self.modem_event_processors = self.all_processors + modem_event_processors
        self.modem_event_processors_sorted = modem_event_processors
        self.modem_event_processors.append(self.interfacesReadyForStreaming) #gets added only after we split up the sorted vs not

        self.modem_processors = []
        self.modem_processors.append(self.modemStats)

        self.session_processors = []
        self.session_processors.append(self.streamSessionStart)
        self.session_processors.append(self.streamSessionEnd)
        self.session_processors.append(self.streamSessionStartServer)
        self.session_processors.append(self.streamSessionEndServer)
        self.session_processors.append(self.streamSessionStartInVersion5)
        self.session_processors.append(self.streamSessionStartSolo)
        self.session_processors.append(self.streamSessionEndSolo)
        self.session_processors.append(self.symanticSesssionId)
        self.session_processors.append(self.streamSessionStartDataBridge)
        self.session_processors.append(self.streamSessionEndDataBridge)
        self.session_processors.append(self.streamSessionStartDataBridgeMultiPath)
        self.session_processors.append(self.streamSessionEndDataBridgeMultiPath)

    @classmethod
    def _print(cls, timestamp, message, filename):
        print("{0!s}: {1!s}".format(timestamp, message))

    def _findPattern(self, line, filename, pattern, message):
        match = re.search(pattern, line.raw)
        if match:
            self._print(line.datetime, message, filename)
            return True
        return False

    def _findPatternWithGroup(self, line, filename, pattern, message):
        match = re.search(pattern, line.raw)
        if match:
            if ConnectivitySummary.instance().on:
                ConnectivitySummary.instance().addLogLine(match.group(1), line, message.format(match.group(1)))
            else:
                self._print(line.datetime,
                            message.format(match.group(1)),
                            filename)
            # return True
        # return False
        return match

    def _findPatternWithGroupOneTwo(self, line, filename, pattern, message):
        match = re.search(pattern, line.raw)
        if match:
            if ConnectivitySummary.instance().on:
                ConnectivitySummary.instance().addLogLine(match.group(1), line, message.format(match.group(1), match.group(2)))
            else:
                self._print(line.datetime, message.format(match.group(1), match.group(2)), filename)
        return match

    def _findPatternWithGroupOneTwoThree(self, line, filename, pattern, message):
        match = re.search(pattern, line.raw)
        if match:
            if ConnectivitySummary.instance().on:
                ConnectivitySummary.instance().addLogLine(match.group(1), line, message.format(match.group(1), match.group(2), match.group(3)))
            else:
                self._print(line.datetime, message.format(match.group(1), match.group(2), match.group(3)), filename)
        return match

    def _findPatternWithGroupOneThree(self, line, filename, pattern, message):
        match = re.search(pattern, line.raw)
        if match:
            if ConnectivitySummary.instance().on:
                ConnectivitySummary.instance().addLogLine(match.group(1), line, message.format(match.group(1), match.group(3)))
            else:
                self._print(line.datetime, message.format(match.group(1), match.group(3)), filename)
        return match

    @classmethod
    def _printCsvBitrateTotal(cls, timestamp, total_bw, video_bw, notes, filename):
        print("{0!s},{1!s},{2!s},{3!s}".format(timestamp.strftime('%Y-%m-%d %H:%M:%S'), total_bw, video_bw, notes))

    @classmethod
    def _printCsvModemBwStatistics(cls, timestamp, modem, total_bw, loss_bw, ex_sm_up, s_round_trip, ex_sm_round_trip, min_sm_round_trip, notes, filename):
        print("Modem{1!s}\t{0!s}\t{2!s}\t{3!s}\t{4!s}\t{5!s}\t{6!s}\t{7!s}\t{8!s}".format(timestamp.strftime('%Y-%m-%d %H:%M:%S'), modem, total_bw, loss_bw, ex_sm_up, s_round_trip, ex_sm_round_trip, min_sm_round_trip, notes))

    @classmethod
    def _printCsvModemBwStatisticsDb(cls, timestamp, modem, total_bw, loss_bw, delay, notes, filename):
        print("Modem{1!s}\t{0!s}\t{2!s}\t{3!s}\t{4!s}\t{5!s}".format(timestamp.strftime('%Y-%m-%d %H:%M:%S'), modem, total_bw, loss_bw, delay, notes))

    def currentOperator(self, line, filename):
        """  USB port 6: Current operator: Vodafone, technology: 4G ( """

        did_match = self._findPatternWithGroupOneTwoThree(line, filename,
                                                  r"INFO: ([^\:]+)\: Current operator\: (.*), technology: (.*) \(",
                                                  "   {0!s} Current Operator: " + CYELLOW + "{1!s}" + CEND + " Tech " + CYELLOW + "{2!s}" + CEND)
        return did_match

    def linkRedyForStreaming(self, line, filename):
        """ 2022-06-25 12:55:37.375058+00:00: corecard eaglenest (9087.634505)(1131.1563247728):INFO: USB port 2: Link is ready for streaming: ({'product': '9071', 'vendor': '1199', 'description': 'T-Mobile', 'deviceIndex': 4, 'usbPort': 1, 'deviceInstance': <eaglenest.usb.ioexpanderport.IOExpanderPort instance at 0x75047440>, 'modemVendor': 'Sierra', 'netmask': '255.255.255.248', 'bindToPort': 0, 'operatorNumeric': None, 'modemType': 'MC7455', 'imei': '359072061914285', 'iccid': '8931088617085078933', 'linkName': 'wwan3', 'technology': '4G', 'operatorName': None, 'plmn': '20408', 'overrideName': {'onlyIf': {'pid': '0000', 'name': None, 'vid': '0000'}, 'name': None}, 'servingPlmn': '26201', 'attached': True, 'operatorSelectionMode': 'automatic', 'localAddress': '10.244.45.27', 'activeSim': 'A', 'gateway': '10.244.45.28', 'isCurrentlyRoaming': True, 'dnsServers': ['194.151.228.34', '194.151.228.18'], 'rssi': -86}) (eaglenest/devices.py:180)"""

        pattern = r"INFO: ([^\:]+)\: Link is ready for streaming: \((.+)\)\s+\(eagle"
        match = re.search(pattern, line.raw)
        if match:
            raw_usb_port_info = match.group(2)
            to_remove = r"\<[^\>]*?\>"
            # print(line.raw)
            # print(match.group(2))
            # print(re.sub(to_remove,"''",raw_usb_port_info))
            usb_port_info = eval(re.sub(to_remove,"''",raw_usb_port_info))
            iccid = ICCID(usb_port_info.get('iccid'))
            output = "   Link ready for streaming, {0!s}: Description: {1!s}, modemType: {2!s}, ICCID: {3!s} [{9!s}], tech: {4!s}, operatorName: {5!s}, activeSIM: {6!s}, isRoaming: {7!s}, rssi: {8!s}".format(match.group(1), usb_port_info.get('description'), usb_port_info.get('modemType'), usb_port_info.get('iccid'), usb_port_info.get('technology'), usb_port_info.get('operatorName'), usb_port_info.get('activeSim'), usb_port_info.get('isCurrentlyRoaming'), usb_port_info.get('rssi'), iccid.sim_provider)
            # print(usb_port_info)
            # print()
            if ConnectivitySummary.instance().on:
                ConnectivitySummary.instance().addLogLine(match.group(1), line, output)
            else:
                self._print(line.datetime,output,filename)
            return True
            # exit(0)
        return False

    def linkLine(self, line, filename):
        """2022-08-13 13:10:59.913542+01:00: corecard eaglenest (120.288513)(1409.1109120144):INFO: USB port 3: Link <Link name: eth2, local address: 192.168.11.100, gateway: 192.168.11.1, dns servers: ['192.168.11.1'], netmask: 255.255.255.0> setup successfully (eaglenest/lan/connectethernetlink.py:27)"""
        did_match = self._findPatternWithGroupOneTwo(line, filename,
                                                  r"INFO: ([^\:]+)\: Link\s+\<([^\>]+)\>",
                                                  "   " + CBLUE + "Link: " + CEND + " {0!s} {1!s}")
        return did_match

    def dhcpLinkLine(self, line, filename):
        """2022-08-13 13:12:24.022519+01:00: corecard eaglenest (204.395904)(1409.1095296144):INFO: wlan0: DHCP link: <Link name: wlan0, local address: 192.168.11.161, gateway: 192.168.11.110, dns servers: ['192.168.11.110'], netmask: 255.255.255.0> is ready after: 1 attempts (eaglenest/lan/dhcp.py:137)"""
        did_match = self._findPatternWithGroupOneTwo(line, filename,
                                                  r"INFO: ([^\:]+)\: DHCP link\:\s+\<([^\>]+)\>",
                                                  "   " + CBLUE + "DHCP Link: " + CEND + "{0!s} {1!s}")
        return did_match



    def manualOperatorSelect(self, line, filename):
        """USB port 6: Setting modem to manually selected operator. mccmnc: 26202"""

        did_match = self._findPatternWithGroupOneTwo(line, filename,
                                                  r"INFO: ([^\:]+)\: Setting modem to manually selected operator. mccmnc: (\d*)",
                                                  "   {0!s} Manually selecting operator: {1!s}")
        return did_match

    def roamingService(self, line, filename):
        """USB port 6: Finished cellular network selection per roaming distribution rules, selected operator: 26202"""

        did_match = self._findPatternWithGroupOneTwo(line, filename,
                                                  r"INFO: ([^\:]+)\: Finished cellular network selection per roaming distribution rules, selected operator: (\d*)",
                                                  "   {0!s} Roamning service selected operator: {1!s}")
        return did_match

    def linkConnected(self, line, filename):
        """USB port 6: Link connected. APN: fast.m2m"""

        did_match = self._findPatternWithGroupOneTwo(line, filename,
                                                  r"INFO: ([^\:]+)\: Link connected. APN: ([^\s]*)",
                                                  "   {0!s} Link connect with apn: {1!s}")
        return did_match

    def qmiLink(self, line, filename):
        """USB port 6: QMI link: <Link name: wwan11, local address: 10.7.85.42, gateway: 10.7.85.41, dns servers: ['194.151.228.34', '194.151.228.18'], netmask: 255.255.255.252> is ready after: 1 attempts"""

        did_match = self._findPatternWithGroupOneTwoThree(line, filename,
                                                  r"INFO: ([^\:]+)\: QMI link: \<([^\>]*?)\> is ready after: (\d*) attempts",
                                                  "   {0!s} QMI Link made after {2!s} attempts: {1!s}")
        return did_match




    def csvBitrateTotal(self, line, filename):
        pattern = r"Detected (flow|congestion) in outgoing queue \(available \<Bandwidth: (\d+)kbps\>\): Setting bitrate to \<Bandwidth: (\d+)kbps\>"
        match = re.search(pattern, line.raw)
        if match:
            self._printCsvBitrateTotal(line.datetime, match.group(2), match.group(3), '', filename)
            return True
        return False

    @classmethod
    def modemStats(cls, line, filename):
        pattern = r"Modem Statistics for modem"
        match = re.search(pattern, line.raw)
        if match:
            ModemSummary.instance().parseLine(line)
            return True
        return False

    def csvBitrateTotalVersion50(self, line, filename):
        pattern = r"Detected flow in outgoing queue \(potential (\d+) kbps\): Setting bitrate to (\d+) kbps"
        match = re.search(pattern, line.raw)
        if match:
            self._printCsvBitrateTotal(line.datetime, match.group(1), match.group(2), '', filename)
            return True
        return False

    def csvBitrateCongestionTotal(self, line, filename):
        pattern = r"Detected congestion in outgoing queue:  drain time = (\d+) ms, potential bandwidth (\d+) kbps: Setting bitrate to (\d+) kbps"
        match = re.search(pattern, line.raw)
        if match:
            self._printCsvBitrateTotal(line.datetime, match.group(2), match.group(3), '', filename)
            return True
        return False

    def csvModemBwStatistics(self, line, filename):
        pattern = r"Modem Statistics for modem (\d+): potentialBW (\d+)k?bps, loss \((\d+)\%\), extrapolated smooth upstream delay \((\d+)ms\), shortest round trip delay \((\d+)ms\), extrapolated smooth round trip delay \((\d+)ms\), minimum smooth round trip delay \((\d+)ms\)"
        match = re.search(pattern, line.raw)
        if match:
            self._printCsvModemBwStatistics(line.datetime, match.group(1), match.group(2), match.group(3), match.group(4), match.group(5), match.group(6), match.group(7), '', filename)
            return True
        return False

    def csvModemBwStatisticsDb(self, line, filename):
        """ Match after following line (example): INFO:Modem Statistics for modem 4: 55kbps, 0% loss, 3ms delay (../../../cpp/Databridge/Bonding/PeriodicalStatisticsTrace.h:47) """

        pattern = r"Modem Statistics for modem (\d+): (\d+)k?bps, (\d+)\% loss, (\d+)ms delay "
        match = re.search(pattern, line.raw)
        if match:
            self._printCsvModemBwStatisticsDb(line.datetime, match.group(1), match.group(2), match.group(3), match.group(4), '', filename)
            return True
        return False

    def csvBitrateStreamSessionStart(self, line, filename):
        pattern = r"Entering state \"StartStreamer\" with args: \(\).+'collectorAddressList'\: \[\[u?'([\d\.]+)', \d+\]\]"
        match = re.search(pattern, line.raw)
        if match:
            self._printCsvBitrateTotal(line.datetime, 0, 0, 'Stream start', filename)
            return True
        return False

    def csvBitrateStreamSessionEnd(self, line, filename):
        pattern = r"Entering state \"StopStreamer\""
        match = re.search(pattern, line.raw)
        if match:
            self._printCsvBitrateTotal(line.datetime, 0, 0, 'Stream end', filename)
            return True
        return False

    def memoryStreamSessionStart(self, line, filename):
        pattern = r"Entering state \"StartStreamer\" with args: \(\).+'collectorAddressList'\: \[\[u?'([\d\.]+)', \d+\]\]"
        match = re.search(pattern, line.raw)
        if match:
            self._print(line.datetime, '<~ Stream start', filename)
            return True
        return False

    def memoryStreamSessionEnd(self, line, filename):
        pattern = r"Entering state \"StopStreamer\""
        match = re.search(pattern, line.raw)
        if match:
            self._print(line.datetime, '~> Stream end', filename)
            return True
        return False

    def memoryStreamSessionStartServer(self, line, filename):
        pattern = r"Entered state \"CollectorStarting\""
        match = re.search(pattern, line.raw)
        if match:
            self._print(line.datetime, '<~ Stream start', filename)
            return True
        return False

    def memoryStreamSessionEndServer(self, line, filename):
        pattern = r"Entering state \"CollectorStopping\""
        match = re.search(pattern, line.raw)
        if match:
            self._print(line.datetime, '~> Stream end', filename)
            return True
        return False

    def memoryStreamSessionStartDataBridgeUnit(self, line, filename):
        pattern = r"Entering state \"StartDatabridgeStreamer\" with args: \(\).+'collectorAddress'\: \(\[u?'([\d\.]+)'\], \d+\)"
        match = re.search(pattern, line.raw)
        if match:
            self._print(line.datetime, '<~ Stream start', filename)
            return True
        return False

    def memoryStreamSessionEndDataBridgeUnit(self, line, filename):
        pattern = r"Entering state \"StopCollectorAndStreamer\""
        match = re.search(pattern, line.raw)
        if match:
            self._print(line.datetime, '~> Stream end', filename)
            return True
        return False

    def csvModemBwStatisticsStreamSessionStart(self, line, filename):
        pattern = r"Entering state \"StartStreamer\" with args: \(\).+'collectorAddressList'\: \[\[u?'([\d\.]+)', \d+\]\]"
        match = re.search(pattern, line.raw)
        if match:
            self._printCsvModemBwStatistics(line.datetime, '', 0, 0, 0, 0, 0, 0, 'Stream start', filename)
            return True
        return False

    def csvModemBwStatisticsStreamSessionStartDb(self, line, filename):
        pattern = r"INFO:Entering state \"StartDatabridgeStreamer\""
        match = re.search(pattern, line.raw)
        if match:
            self._printCsvModemBwStatisticsDb(line.datetime, '', 0, 0, 0, 'Stream start', filename)
            return True
        return False

    def csvModemBwStatisticsStreamSessionStartDbGw(self, line, filename):
        pattern = r"INFO:Entered state \"CollectorStarting\""
        match = re.search(pattern, line.raw)
        if match:
            self._printCsvModemBwStatisticsDb(line.datetime, '', 0, 0, 0, 'Stream start (GW)', filename)
            return True
        return False

    def csvModemBwStatisticsStreamSessionEnd(self, line, filename):
        pattern = r"Entering state \"StopStreamer\""
        match = re.search(pattern, line.raw)
        if match:
            self._printCsvModemBwStatistics(line.datetime, '', 0, 0, 0, 0, 0, 0, 'Stream end', filename)
            return True
        return False

    def csvModemBwStatisticsStreamSessionEndDb(self, line, filename):
        pattern = r"INFO:Entering state \"StopCollectorAndStreamer\""
        match = re.search(pattern, line.raw)
        if match:
            self._printCsvModemBwStatisticsDb(line.datetime, '', 0, 0, 0, 'Stream end', filename)
            return True
        return False

    def csvModemBwStatisticsStreamSessionEndDbGw(self, line, filename):
        pattern = r"INFO:Entering state \"CollectorStopping\" with args:"
        match = re.search(pattern, line.raw)
        if match:
            self._printCsvModemBwStatisticsDb(line.datetime, '', 0, 0, 0, 'Stream end (GW)', filename)
            return True
        return False

    def csvModemBwStatisticsModemDisconnected(self, line, filename):
        pattern = r"INFO:Modem removed id: (\d+)"
        match = re.search(pattern, line.raw)
        if match:
            self._printCsvModemBwStatistics(line.datetime, match.group(1), '', '', '', '', '', '', 'Modem disconnected', filename)
            return True
        return False

    def csvModemBwStatisticsModemDisconnectedDb(self, line, filename):
        pattern = r"INFO:Modem removed id: (\d+)"
        match = re.search(pattern, line.raw)
        if match:
            self._printCsvModemBwStatistics(line.datetime, match.group(1), '', '', '', 'Modem disconnected', filename)
            return True
        return False

# Unit video mode

    def maxQualityAtLowDelay(self, line, filename):
        return self._findPattern(line, filename,
                                  r"Starting Video Application: Jitter Delay = 0\.78, Early Gap Detection Delay = 0\.78, Profile = maxquality",
                                  "   Unit tried to use maxquality with low delay - move the delay up then down")

    def i2cBusRecovery(self, line, filename):
        return self._findPattern(line, filename,
                                  r"Initiating i2c bus recovery",
                                  "   i2c bus recovery")

    def leastCostBondingActivatedForChargeableLinks(self, line, filename):
        """ Match after following line (example): INFO:Setting group of modems - chargeable-links: Priority: 1, Bandwidth limit: 58000 kbps, burst: 30 ms (../../cpp/StreamerEngine/Bonding/MultiScheduler.h:36)"""

        return self._findPattern(line, filename,
                                  r"INFO:Setting group of modems - chargeable-links: Priority: 1, Bandwidth limit: \d+ kbps, burst: \d+ ms",
                                  "   Least Cost Bonding is activated (Priority: Modems)")

    def leastCostBondingActivatedForFreeLinks(self, line, filename):
        """ Match after following line (example): INFO:Setting group of modems - free-links: Priority: 1, Bandwidth limit: 58000 kbps, burst: 30 ms (../../cpp/StreamerEngine/Bonding/MultiScheduler.h:36)"""

        return self._findPattern(line, filename,
                                  r"INFO:Setting group of modems - free-links: Priority: 1, Bandwidth limit: \d+ kbps, burst: \d+ ms",
                                  "   Least Cost Bonding is activated (Priority: ETH/WiFi)")

    def potentialBandwidthIsZero(self, line, filename):
        """ Match after following line (example): INFO:Shooting Mode changed level (potential 0 kbps): Setting bitrate to 50 kbps, lastBitrate = 50 kbps, spare = 0.10, rtp fragmenter maximum packet size = 450 bytes (../../cpp/StreamerEngine/Applications/RTPApplications/Video/AdaptiveVideoParameters/AdaptiveVideoParameters.h:280) """

        return self._findPattern(line, filename,
                                  r"Shooting Mode changed level \(potential 0 kbps\)\: Setting bitrate to 50 kbps",
                                  CRED + "    Stream hit 0 Kbps!" + CEND)

    def failedToReadRegister(self, line, filename):
        """ Match after following line (example): corecard kernel: [13831.912597] smsc95xx 1-1.2.3:1.0: eth1: Failed to read register index 0x00000114 """

        return self._findPatternWithGroup(line, filename,
                                             r"([^\:\s]+)\: Failed to read register index",
                                             "  Kernel failed to read a register for {0!s} (bus overload?)")

    def portDisabledByEmi(self, line, filename):
        """ Match after following line (example): """

        return self._findPattern(line, filename,
                                  r"port \d+ disabled by hub \(EMI\?\), re\-enabling",
                                  CRED + "    A port was disabled by the EMI issue" + CEND)

    def portResetByEmi(self, line, filename):
        """ Match after following line (example): """

        return self._findPatternWithGroup(line, filename,
                                             r"port (\d+) disabled by hub \(EMI\?\), detected only \(no resetting\)",
                                             CRED + "    EMI issue detected only (no resetting), port {0!s}" + CEND)

    def natTableFull(self, line, filename):
        """ Match after following line (example): sitara kernel: [ 1103.905914] nf_conntrack: table full, dropping packet. """

        return self._findPattern(line, filename,
                                  r"nf_conntrack\: table full\, dropping packet",
                                  "   NAT table was full and dropped backfire packets")

    def modemInterfaceDisconnectedNotReachingInternet(self, line, filename):
        """ Match after following line (example): ERROR:usb port 3: link wwan8 did not reach the Internet after 3 retries, aborting (eaglenest/networking/reachinternet.py:53). Modem disconnected because didn't reach internet after 3 retries. """

        return self._findPatternWithGroup(line, filename,
                                             r"ERROR:usb port (\d+): link [\w\s\d]+? did not reach the Internet after 3 retries, aborting",
                                             CYELLOW + "   Modem in usb port {0!s} disconnected because didn\'t reached the Internet" + CEND)

    def modemInterfaceDisconnectedNotReachingInternetVersion7(self, line, filename):
        """ Match after following line (example): ERROR: USB port 8: Link: wwan6 did not reach the Internet after: 3 attempts, aborting (eaglenest/networking/reachinternet.py:61) """

        return self._findPatternWithGroup(line, filename,
                                             r"ERROR: USB port (\d+): Link: [\w\s\d]+? did not reach the Internet after: \d+ attempts, aborting",
                                             CYELLOW + "   Modem in usb port {0!s} disconnected because didn\'t reached the Internet" + CEND)

    def bandwidthLimitForModemSetting(self, line, filename):
        """ Match after following line (example): INFO:usb port 8: Setting hard bandwidth limit of 1000 KBPS for device <SysFSDevice /sys/devices/platform/ehci-omap.0/usb1/1-1/1-1.3/1-1.3.3> (eaglenest/usb/powercontroledport.py:220)"""

        return self._findPatternWithGroupOneTwo(line, filename,
                                                 r"INFO:usb port (\d+): Setting hard bandwidth limit of (\d+) KBPS for device",
                                                 "   Modem in usb port {0!s}: setting bandwidth limit to" + CBLINK + " {1!s}" + CEND + " Kbps")

    def modemInterfaceDisconnectedNotReachingInternetAfterThreeRetries(self, line, filename):
        """ Match after following line (example): ERROR:usb port 3: Failed to setup link wwan8 for networking: link wwan8 did not reach the Internet after 3 retries, aborting (eaglenest/networking/setuplink.py:21) """

        return self._findPatternWithGroup(line, filename,
                                             r"ERROR:usb port (\d+): Failed to setup link [\w\s\d]+? for networking: link [\w\s\d]+? did not reach the Internet after 3 retries, aborting",
                                             CYELLOW + "   Modem in usb port {0!s} failed to setup link for networking because didn\'t reached the Internet" + CEND)

    def modemInterfaceDisconnectedNotReachingInternetAfterThreeRetriesVersion7(self, line, filename):
        """ Match after following line (example): ERROR: USB port 3: Failed to setup link wwan8 for networking: Link: wwan8 did not reach the Internet after: 3 attempts, aborting (eaglenest/networking/setuplink.py:21) """

        return self._findPatternWithGroup(line, filename,
                                             r"ERROR: USB port (\d+): Failed to setup link [\w\s\d]+? for networking: Link: [\w\s\d]+? did not reach the Internet after: 3 attempts, aborting",
                                             CYELLOW + "   Modem in usb port {0!s} failed to setup link for networking because didn\'t reached the Internet" + CEND)

    def ethernetInterfaceCableDisconnectedRemoved(self, line, filename):
        """ #Match after following line (example): INFO:eth0: Link <Link name: eth0, local address: 192.168.5.106, gateway: 192.168.5.254, dns servers: ['192.168.5.5'], netmask: 255.255.255.0> cable disconnected (eaglenest/lan/connectethernetlink.py:33) """

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:eth(\d+): Link .+cable disconnected",
                                             CYELLOW + "   Ethernet interface eth{0!s} was disconnected/disabled, link is down" + CEND)

    def ethernetInterfaceCableDisconnectedRemovedVersion7(self, line, filename):
        """ Match after following line (example): INFO: eth1: Link <Link name: eth1, local address: 172.12.100.249, gateway: 172.12.100.93, dns servers: ['172.12.100.93'], netmask: 255.255.255.0> disconnected (eaglenest/lan/connectethernetlink.py:34) """

        return self._findPatternWithGroup(line, filename,
                                             r"INFO: eth(\d+): Link .+disconnected",
                                             CYELLOW + "   Ethernet interface eth{0!s} was disconnected/disabled, link is down" + CEND)

    def wifiInterfaceDisconnectedDisabled(self, line, filename):
        """ Match after following line (example): INFO:wlan0: removing route for link wlan0 (eaglenest/networking/route.py:46)"""

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:wlan(\d+): removing route for link wlan(\d+)",
                                             CYELLOW + "   WiFi interface wlan{0!s} was disconnected/disabled, link is down" + CEND)

    def wifiInterfaceDisconnectedDisabledVersion7(self, line, filename):
        """ Match after following line (example): INFO: wlan0: removing route for link wlan0 (eaglenest/networking/route.py:42) """

        return self._findPatternWithGroup(line, filename,
                                             r"INFO: wlan(\d+): removing route for link wlan\d+",
                                             CYELLOW + "   WiFi interface wlan{0!s} was disconnected/disabled, link is down" + CEND)

    def modemInterfaceDisconnectedDisabled(self, line, filename):
        """ Match after following line (example): ERROR:usb port 2: Unable to dial modem: device <SysFSDevice /sys/devices/soc0/soc.0/2100000.aips-bus/2184200.usb/ci_hdrc.1/usb1/1-1/1-1.2> not alive (eaglenest/usb/powercontroledport.py:183)"""

        return self._findPatternWithGroup(line, filename,
                                             r"ERROR:usb port (\d+): Unable to dial modem: .+ not alive",
                                             CYELLOW + "   Modem in usb port {0!s} was disconnected/disabled, link is down" + CEND)

    def ethernetInterfaceConnected(self, line, filename):
        """ Match after following line (example): INFO:eth1: Link is ready for streaming: ({'deviceIndex': 1, 'description': 'Ethernet', 'macAddress': '78:51:0c:00:c8:f5', 'deviceInstance': <EthernetPort(Thread-5, started daemon 1968174176)>, 'powerOverEthernet': False, 'localAddress': '192.168.2.59', 'dnsServers': ['192.168.2.1'], 'netmask': '255.255.255.0', 'fixedethernetport': True, 'bindToPort': 0, 'bridged': False, 'staticConfiguration': False, 'linkName': 'eth1', 'gateway': '192.168.2.1'}) (eaglenest/devices.py:118) """

        return self._findPatternWithGroupOneTwo(line, filename,
                                                   r"INFO:eth(\d+): Link is ready for streaming: .+\'deviceIndex\'\: (\d+)\,",
                                                   CGREEN + "   Ethernet interface eth{0!s} was connected, device index: Modem {1!s}" + CEND)

    def ethernetInterfaceConnectedVersion7(self, line, filename):
        """ Match after following line (example): INFO: eth1: Link is ready for streaming: ({'xTender': False, 'description': 'Ethernet', 'macAddress': '60:38:e0:e3:0f:f8', 'deviceInstance': <EthernetPort(Thread-5, started daemon 1095226512)>, 'netmask': '255.255.255.0', 'fixedethernetport': True, 'bindToPort': 0, 'staticConfiguration': False, 'linkName': 'eth1', 'gateway': '192.168.1.1', 'deviceIndex': 1, 'powerOverEthernet': False, 'localAddress': '192.168.1.39', 'bridged': False, 'dnsServers': ['192.168.1.248', '127.0.0.1']}) (eaglenest/devices.py:142) """

        return self._findPatternWithGroupOneTwo(line, filename,
                                                   r"INFO: eth(\d+): Link is ready for streaming: .+\'deviceIndex\'\: (\d+)\,",
                                                   CGREEN + "   Ethernet interface eth{0!s} was connected, device index: Modem {1!s}" + CEND)

    def wifiInterfaceConnected(self, line, filename):
        """ Match after following line (example): INFO:wlan0: Link is ready for streaming: ({'deviceIndex': 1, 'description': 'iPhone', 'macAddress': '78:51:0c:00:d1:d5', 'deviceInstance': <WiFi(Thread-8, started daemon 1094136976)>, 'linkName': 'wlan0', 'fixedwifiport': True, 'wifiNetworkName': 'iPhone'}) (eaglenest/devices.py:119) """

        return self._findPatternWithGroupOneTwo(line, filename,
                                                 r"INFO:wlan(\d+): Link is ready for streaming: .+\'deviceIndex\'\: (\d+)\,",
                                                 CGREEN + "   WiFi interface wlan{0!s} was connected, device index: Modem {1!s}" + CEND)

    def modemInterfaceConnected(self, line, filename):
        """ Match after following line (example): INFO:usb port 7: Link is ready for streaming: ({'product': '0041', 'vendor': '13b1', 'description': 'Ethernet', 'usbPort': 'eth1', 'deviceInstance': <DronePort(Thread-17, started daemon 1111651472)>, 'netmask': '255.255.255.0', 'bindToPort': 0, 'operatorNumeric': None, 'linkName': 'eth1', 'localAddress': '192.168.1.39', 'overideName': {'onlyIf': {'pid': '0000', 'name': None, 'vid': '0000'}, 'name': None}, 'operatorName': None, 'deviceIndex': 8, 'technology': '', 'attached': True, 'operatorSelectionMode': 'automatic', 'activeSim': '', 'gateway': '192.168.1.1', 'isCurrentlyRoaming': False, 'dnsServers': ['192.168.1.248', '127.0.0.1']}) (eaglenest/devices.py:118)"""

        return self._findPatternWithGroupOneTwo(line, filename,
                                                     r"INFO:usb port (\d+): Link is ready for streaming: .+\'deviceIndex\'\: (\d+)\,",
                                                     CGREEN + "   Modem interface in usb port {0!s} was connected, device index: Modem {1!s}" + CEND)

    def modemInterfaceConnectedVersion7(self, line, filename):
        """ Match after following line (example): INFO: USB port 5: Link is ready for streaming: ({'username': '', 'deviceIndex': 6, 'product': '9071', 'vendor': '1199', 'description': 'T-Mobile', 'usbPort': 4, 'deviceInstance': <IOExpanderPort(Thread-22, started daemon 1099953296)>, 'netmask': '255.255.255.248', 'phonenumber': '*99#', 'bindToPort': 0, 'operatorNumeric': None, 'isCurrentlyRoaming': False, 'linkName': 'wwan4', 'password': '', 'technology': '4G', 'operatorName': None, 'plmn': '310260', 'overrideName': {'onlyIf': {'pid': '0000', 'name': None, 'vid': '0000'}, 'name': None}, 'servingPlmn': '310260', 'attached': True, 'operatorSelectionMode': 'automatic', 'localAddress': '29.7.246.99', 'activeSim': '', 'gateway': '29.7.246.100', 'apns': [''], 'dnsServers': ['10.177.0.34', '10.177.0.210']}) (eaglenest/devices.py:142)"""

        return self._findPatternWithGroupOneTwo(line, filename,
                                                     r"INFO: USB port (\d+): Link is ready for streaming: .+\'deviceIndex\'\: (\d+)\,",
                                                     CGREEN + "   Modem interface in usb port {0!s} was connected, device index: Modem {1!s}" + CEND)

    def modemInterfaceRemoved(self, line, filename):
        """ Match after following line (example): WARNING:usb port 1: QMI modem was physically removed (eaglenest/usb/sierraqmidriver.py:175) """

        return self._findPatternWithGroup(line, filename,
                                             r"WARNING:usb port (\d+):.+was physically removed",
                                             CYELLOW + "   Modem in usb port {0!s} was removed..." + CEND)

    def modemInterfaceRemovedVersion7(self, line, filename):
        """ Match after following line (example): WARNING: USB port 1: QMI modem was physically removed (eaglenest/usb/sierraqmidriver.py:221) """

        return self._findPatternWithGroup(line, filename,
                                             r"WARNING: USB port (\d+):.+was physically removed",
                                             CYELLOW + "   Modem in usb port {0!s} was removed..." + CEND)

    def avic_videores(self, line, filename):
        """ Match after following line (example): """

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:AVIC client success: Setting video parameters according to ([^\s]+)",
                                             "Resolution is: {0!s}")

    def videores(self, line, filename):
        """ Match after following line (example): """

        return self._findPatternWithGroup(line, filename,
                                             r"reported resolution \[(\d+:\d+)\]",
                                             "Resolution is: {0!s}")

    def detected_videores(self, line, filename):
        """ Match after following line (example): INFO:Detected input resolution change. Set encode resolution to [1280:720] (../../cpp/CentaurusMediaApplication/Video/Encoder.h:512)"""

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:Detected input resolution change\. Set encode resolution to \[(\d+:\d+)\]",
                                             "Resolution is: {0!s}")
    def shotingModeChange(self, line, filename):
        """ Match after following line (example): vic python (1734.500557)(355.370):INFO:Shooting Mode Changed level from 7 to 2 (../../cpp/StreamerEngine/Applications/RTPApplications/Video/AdaptiveVideoParameters/AdaptiveVideoParameters.h:223) """

        return self._findPatternWithGroupOneTwo(line, filename,
                                             r"INFO:Shooting Mode Changed level from (\d+) to (\d+)",
                                             "Shooting Mode Changed level from {0!s} to {1!s}")

    def switchingHub(self, line, filename):
        """ Match after following line (example): corecard boss100 (165.150268)(1248.1090368656):INFO:Switched remote control hub to ws://193.34.250.15:10022 (remotecontrol/hubselector.py:16) """

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:Switched remote control hub to ([^\s]+)",
                                             "   Trying to connect to hub:" + CRED + " {0!s}" + CEND)
    def switchingHubVersion7(self, line, filename):
        """ Match after following line (example): """

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:Will try to connect to the next hub ([^\s]+)",
                                             "   Trying to connect to hub:" + CRED + " {0!s}" + CEND)

    def cameraStatusConnectAvic(self, line, filename):
        """ Match after following line (example): INFO:avic input parameters were changed to: connected: True, videoInputStatus: SDI, interlaced: True, width: 1920, height: 1080, frameRate: 25, mode: 1080i50 (avicmediaapplication/inputeventhandler.py:30). Camera connected AVIC, video resolution and input type. """

        return self._findPatternWithGroupOneTwo(line, filename,
                                                 r"INFO:avic input parameters were changed to: connected: True, videoInputStatus: ([^\,]+).+mode: ([^\s]+)",
                                                 CGREEN + "   Camera connected, video input: {0!s}, resolution: {1!s}" + CEND)

    def monitorChannelReadiness(self, line, filename):
        """ Match after following line (example): INFO:Got status message from 'Boss1100_189250943923922_Instance1': 'collecting' (boss100/monitorchannelreadiness.py:80) """

        return self._findPatternWithGroupOneTwo(line, filename,
                                                 r"INFO:Got status message from \'([\d\.\_\(\)a-zA-Z]+)\': \'([\d\.\(\)a-zA-Z]+)\'",
                                                 "   Channel {0!s} status:" + CVIOLET + " {1!s}" + CEND)

    def destinationIdSettings(self, line, filename):
        """ Match after following line (example): INFO:Setting attribute destination = None (was: 2002343) (common/persistent.py:21) """

        return self._findPatternWithGroupOneTwo(line, filename,
                                                 r"INFO:Setting attribute destination = ([\d\.\_\(\)a-zA-Z]+) \(was: ([\d\.\(\)a-zA-Z]+)\)",
                                                 "   Solo unit destination set to:" + CVIOLET + " {0!s}" +CEND + " was:" + CVIOLET + " {1!s}" + CEND)

    def cameraStatusDisconnectAvic(self, line, filename):
        """ Match after following line (example): INFO:avic input parameters were changed to: camera disconnected will be sent (avicmediaapplication/inputeventhandler.py:32). Camera disconnected for AVIC """

        return self._findPattern(line, filename,
                                  r"INFO:avic input parameters were changed to: camera disconnected will be sent",
                                  CRED + "   Camera disconnected" + CEND)

    def cameraDisconnectedStatusTimer(self, line, filename):
        """ Match after following line (example): INFO:Start 60 seconds camera disconnected during stream timer (boss100/statemachines/main/video/cameradisconnectduringstreamkeeper.py:28) """

        return self._findPatternWithGroup(line, filename,
                                                 r"INFO:Start (\d+) seconds camera disconnected during stream timer",
                                                 CYELLOW + "   Camera disconnected during stream, timeout is {0!s} seconds" + CEND)

    def cameraDisconnectedStatusTimerError(self, line, filename):
        """ Match after following line (example): INFO:Camera disconnected during stream timeout expired (boss100/statemachines/main/video/cameradisconnectduringstreamkeeper.py:40) """

        return self._findPattern(line, filename,
                                                 r"INFO:Camera disconnected during stream timeout expired",
                                                 CRED + "   Camera disconnected during stream timeout expired!!!" + CEND)

    def stopEncoderAndRecorderState(self, line, filename):
        """ Match after following line (example): INFO:Entered state "StopEncoderAndRecorder" (common/statemachine/state.py:23) """

        return self._findPattern(line, filename,
                                                 r"INFO:Entered state \"StopEncoderAndRecorder\"",
                                                 CVIOLET + "   Stopping encorder and recorder" + CEND)

    def sendingFileDone(self, line, filename):
        """ Match after following line (example): INFO:Sending file done. socket closed (../../cpp/FileTransfer/DataPipe.h:89) """

        return self._findPattern(line, filename,
                                                 r"INFO:Sending file done. socket closed",
                                                 CVIOLET + "   Sending file done" + CEND)

    def startForwardingState(self, line, filename):
        """ Match after following line (example): INFO:Entered state "Forwarding" (common/statemachine/state.py:23) """

        return self._findPattern(line, filename,
                                                 r"INFO:Entered state \"Forwarding\"",
                                                 CVIOLET + "   Starting Forwarding" + CEND)

    def streamSessionStart(self, line, filename):
        """ #Match after following line (example): INFO:Entering state "Streaming" with args: ('Boss1100_233845178526555_Instance1',), {} (common/statemachine/state.py:24) """

        did_match = self._findPatternWithGroup(line, filename,
                                                  r"Entering state \"Streaming\" with args: \('([^']+)'",
                                                  "<~~ Stream start to channel: {0!s}  ")
        # if did_match:
            # SessionTracker.instance().logStart(line.datetime)
        return did_match

    def selectedChannelId(self, line, filename):
        """ Match after following line (example): INFO:Subscribing to Boss1100_159090363131758_Instance1 (remotecontrol/client.py:70)"""

        return self._findPatternWithGroup(line, filename,
                                             r"boss100.+INFO:Subscribing to ([^\s]+)",
                                             "   Selected channel ID: {0!s}")

    def streamSessionStartInVersion5(self, line, filename):
        """ Match after following line (example): INFO:Entering state "StartStreamer" with args: (), {'pipelineType': {'transferProperties': [], 'type': 'liveStreaming'}, 'collectorAddressList': [[u'184.154.39.10', 9001]]} (common/statemachine/state.py:21)"""

        did_match = self._findPatternWithGroup(line, filename,
                                                  r"Entering state \"StartStreamer\" with args: \(\).+'collectorAddressList'\: \[\[u?'([\d\.]+)', \d+\]\]",
                                                  "<~~ Stream start to IP: {0!s}")
        if did_match:
            SessionTracker.instance().logStart(line.datetime)
        return did_match

    def streamSessionStartSolo(self, line, filename):
        """ Match after following line (example): INFO:Entering state "StartDirectStream" with args: (), {} (common/statemachine/state.py:21) """

        did_match = self._findPattern(line, filename,
                                       r"INFO:Entering state \"StartDirectStream\" with args:",
                                       "<~~ Stream start (Solo RTMP)")
        if did_match:
            SessionTracker.instance().logStart(line.datetime)
        return did_match

    def streamSessionEndSolo(self, line, filename):
        """ Match after following line (example): INFO:Entering state "StopDirectStreamer" with args: (), {} (common/statemachine/state.py:21) """

        did_match = self._findPattern(line, filename,
                                       r"INFO:Entering state \"StopDirectStreamer\" with args:",
                                       "~~> Stream end (Solo RTMP)")
        if did_match:
            SessionTracker.instance().logEnd(line.datetime)
        return did_match

    def streamSessionEnd(self, line, filename):
        """ Match after following line (example): INFO:Entering state "StopStreamer" with args: (), {} (common/statemachine/state.py:21). Stream stopped, session end. """

        did_match = self._findPattern(line, filename,
                                       r"Entering state \"StopStreamer\"",
                                       CBLUE + "~~> Stream end (controlled)" + CEND)
        if did_match:
            SessionTracker.instance().logEnd(line.datetime)
        return did_match

    def startSessionType(self, line, filename):
        """ Match after following line (example): INFO:Entering state "StartCollector" with args: (), {'pipelineType': {'transferProperties': [], 'type': 'liveStreaming'}} (common/statemachine/state.py:21)"""

        return self._findPatternWithGroup(line, filename,
                                             r"Entering state \"StartCollector\" with args: \(\).+'type': '([\d\.\(\)a-zA-Z]+)'",
                                             CBLUE + "<~~ Start session type: {0!s}" + CEND)

    def hubConnectionTimeout(self, line, filename):
        return self._findPatternWithGroup(line, filename,
                                             r"Connection failed \(Exception was: Delay on remote control link \(([^\)]+)\)",
                                             CYELLOW + "   Hub connection timeout, time was {0!s}, removing connection" + CEND)

    def hubHubConnectionTimeoutModem(self, line, filename):
        """ Match after following line (example): ERROR:Delay on remote control link (3) is above 12, removing connection (remotecontrol/pingpong.py:23). In case big delay on remote control link connection is removed """

        return self._findPatternWithGroup(line, filename,
                                             r"ERROR:Delay on remote control link \(([\d]+)\) is above 12, removing connection",
                                             CYELLOW + "   Hub connection timeout on modem {0!s}, delay was above 12, removing connection" + CEND)

    def cvicGeneration(self, line, filename):
        """ Match after following line (example): vic kernel: BOARD: CVIC_GEN2"""

        return self._findPatternWithGroup(line, filename,
                                             r"(?:--cvic-board=|BOARD: )CVIC_GEN(\d+)",
                                             " CVIC Generation is: {0!s}")

    def deviceSoftwareVersion(self, line, filename):
        """ Match after following line (example): INFO:Logging for overlord version 6.5.0.C14608.G9d83de178 started (overlord/main.py:9). Returns software version for overlord egg. """

        return self._findPatternWithGroup(line, filename,
                                             r"Logging for (?:overlord|collector) version ([\d\.\(\)a-zA-Z]+)",
                                             "   Software version: {0!s}")

    def videoInputResolution(self, line, filename):
        """ Match after following line (example): """

        return self._findPatternWithGroup(line, filename,
                                             r"Configured HW port properties: (width=\d+, height=\d+)",
                                             "Input resolution: {0!s}")

    def videoEndToEndDelay(self, line, filename):
        """ Match after following line (example): INFO:Setting attribute endToEndDelay = 5 (was: 5) (common/persistent.py:21) """

        return self._findPatternWithGroupOneTwo(line, filename,
                                                 r"INFO:Setting attribute endToEndDelay = ([\d\.]+) \(was\: ([\d\.]+)\)",
                                                 "   E2E delay is set to: {0!s} second(s) (was: {1!s})")

    def unitTotalBandwidthLimitChange(self, line, filename):
        """ Match after following line (example): INFO:Setting attribute bandwidthLimitKbps = 0 (was: 0) (common/persistent.py:21) """

        return self._findPatternWithGroupOneTwo(line, filename,
                                                 r"INFO:Setting attribute bandwidthLimitKbps = (\d+) \(was\: (\d+)\)",
                                                 "   Bandwidth limit is set to:" + CBLINK + " {0!s}" + CEND + "Kbps (was: {1!s})")

    def unitTotalBandwidthLimit(self, line, filename):
        """ Match after following line (example): INFO:Setting MultiScheduler bandwidth restrictor: 6200 Kbps, burstTimeCapacity = 30 ms for precedent application: video with economy mode: Enabled"""

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:Setting MultiScheduler bandwidth restrictor: (\d+) Kbps, burstTimeCapacity = \d+ ms for precedent application: video with economy mode: Enabled",
                                             "   Bandwidth limit is set to:" + CBLINK + " {0!s}" + CEND + " Kbps")

    def sdiVideoInputResolution(self, line, filename):
        """ Match after following line (example): INFO:SDI reported std=11, frameWidth=1920, frameHeight=1080, frameRate=30, interlaced=True, standard=1080i60 (../../cpp/CentaurusMediaApplication/FPGA/SdiDevice.h:149)"""

        return self._findPatternWithGroup(line, filename,
                                             r"NFO:SDI reported std=\d+, frameWidth=\d+, frameHeight=\d+, frameRate=\d+, interlaced=[\d\(\)a-zA-Z]+, standard=([\d\(\)a-zA-Z]+)",
                                             "SDI input resolution: {0!s}")

    def hdmiVideoInputResolution(self, line, filename):
        """ Match after following line (example): INFO:TVP reported std=11, frameWidth=1920, frameHeight=1080, frameRate=30, interlaced=True, standard=1080i60 (../../cpp/CentaurusMediaApplication/FPGA/SdiDevice.h:149)"""

        return self._findPatternWithGroup(line, filename,
                                             r"NFO:TVP reported std=\d+, frameWidth=\d+, frameHeight=\d+, frameRate=\d+, interlaced=[\d\(\)a-zA-Z]+, standard=([\d\(\)a-zA-Z]+)",
                                             "HDMI input resolution: {0!s}")

    def eggCrashSystem(self, line, filename):
        """ Match after following line (example): ERROR:Overlord watched Egg eaglenest, and it terminated unexpectedly with signal 6 (overlord/watchdog.py:28) """

        return self._findPatternWithGroupOneTwo(line, filename,
                                                 r"ERROR:Overlord watched Egg ([^\,]+).+and it terminated unexpectedly with signal (\d+)",
                                                 CRED + "    CRASH! {0!s} terminated unexpectedly, signal {1!s}! (system)" + CEND)

    def eggCrashSoftware(self, line, filename):
        """ Match after following line (example): ERROR:Overlord watched Egg master_collector, and it terminated unexpectedly with exit code 1 (overlord/watchdog.py:38)"""

        return self._findPatternWithGroupOneTwo(line, filename,
                                                 r"ERROR:Overlord watched Egg ([^\,]+).+and it terminated unexpectedly with exit code (\d+)",
                                                 CRED + "    CRASH! {0!s} terminated unexpectedly, exit code {1!s}! (software)" + CEND)

    def eggRestartWarning(self, line, filename):
        """ Match after following line (example): WARNING:Overmind to restart egg eaglenest (overlord/overmind.py:135) """

        return self._findPatternWithGroup(line, filename,
                                             r"WARNING:Overmind to restart egg ([^\s]+)",
                                             CRED + "    RESTART! {0!s} terminated unexpectedly, restarting!" + CEND)

    def eggRestartError(self, line, filename):
        """ Match after following line (example): ERROR:Process master_eaglenest failed on keep-alive. 3/3 failures (or 0/9 times of no initial response). Restarting process (overlord/master/keepalive.py:70) """

        return self._findPatternWithGroup(line, filename,
                                             r"ERROR:Process ([^\s]+).+failed on keep-alive.+Restarting process",
                                             CRED + "    RESTART! {0!s} terminated unexpectedly, restarting!" + CEND)

    def videoInputDisconnectError(self, line, filename):
        """ Match after following line (example): ERROR:Video interrupted (probably different camera connected while streaming) (boss100/statemachine/commonstreamingstate.py:64) """

        return self._findPattern(line, filename,
                                  r"ERROR:Video interrupted \(probably different camera connected while streaming\)",
                                  CRED + "   Video disconnect error" + CEND)

    def pantechIn70AssertionError(self, line, filename):
        """ Match after following line (example): ERROR:Assertion Error! at cpp/Bonding/Modem/List.h:178 (/home/me/builds/building/trunk/cpp/Common/DebugAssert.cpp:8) """

        return self._findPattern(line, filename,
                                  r"ERROR:Assertion Error! at cpp/Bonding/Modem/List\.h:178",
                                  CRED + "   Assertion caused by Pantechs in external 70 usb port" + CEND)

    def sdiCableConnectDisconnect(self, line, filename):
        """ Match after following line (example): vic kernel: SDI: CABLE: cable connected """

        return self._findPatternWithGroup(line, filename,
                                             r"SDI: CABLE: cable ([a-zA-Z]+)",
                                             "   SDI cable" + CVIOLET + " {0!s}" + CEND)

    def hdmiCableConnectDisconnect(self, line, filename):
        """ Match after following line (example): vic kernel: HDMI: CABLE: cable connected """

        return self._findPatternWithGroup(line,
                                             filename,
                                             r"HDMI: CABLE: cable ([a-zA-Z]+)",
                                             "   HDMI cable" + CVIOLET + " {0!s}" + CEND)

    def cameraStatusConnectDisconnectCvic(self, line, filename):
        """ Match after following line (example): INFO:Camera connected (SDI) (StateMachine.cpp:576)"""

        return self._findPatternWithGroup(line, filename,
                                             r"vic.+INFO:Camera ([a-zA-Z]+)",
                                             "   Camera" + CVIOLET + " {0!s}" + CEND)

    def sdiInvalidVideoInputWarning(self, line, filename):
        """ Match after following line (example): WARNING:SDI reported invalid video input (../../cpp/CentaurusMediaApplication/FPGA/SdiDevice.h:145) """

        return self._findPattern(line, filename,
                                  r"WARNING:SDI reported invalid video input",
                                  CRED + "   Error! invalid video input" + CEND)

    def profileQueryErrorAfterUpgrade(self, line, filename):
        """ Match after following line (example): ERROR:Unable to perform query '<boss100.ipctongue.QueryProfile instance at 0x76089350>' to '(u'localhost', 11700)' (common/ipc/query.py:32) """

        return self._findPattern(line, filename,
                                  r"ERROR:Unable to perform query \'\<boss100\.ipctongue\.QueryProfile",
                                  CRED + "   Query to find the profile returned an error, like units that were upgraded from auto instead of fast motion" + CEND)

    def onlineOfflineDuringLiveSession(self, line, filename):
        """ Match after following line (example): ERROR:Illegal event "offline" in state "Streaming" (common/statemachine/state.py:38) """

        return self._findPatternWithGroup(line, filename,
                                             r"Illegal event \"([a-zA-Z]+)\" in state \"Streaming\"",
                                             "   Unit got" + CBLINK + " {0!s}" + CEND + " event while still streaming, it was {0!s} in LUC")

    def onlineOfflineDuringStoreAndForwardSession(self, line, filename):
        """ Match after following line (example): ERROR:Illegal event "offline" in state "StoreAndForward" (common/statemachine/state.py:38) """

        return self._findPatternWithGroup(line, filename,
                                             r"Illegal event \"([a-zA-Z]+)\" in state \"StoreAndForward\"",
                                             "   Unit got" + CBLINK + " {0!s}" + CEND + " event while still forwarding, it was {0!s} in LUC")

    def offlineInIdle(self, line, filename):
        """ Match after following line (example): INFO:Status change: readiness='offline', camera connected=False (handheldremote/devicehandler.py:31) """

        return self._findPattern(line, filename,
                                  r"INFO:Status change: readiness=\'offline\'",
                                  "   Unit got" + CBLINK + " offline" + CEND + " event in Idle mode, it was offline in LUC")

    def hubConnectAttemptUnit(self, line, filename):
        """ Match after following line (example): INFO:Next modem 6 (3) hub URL "ws://hub1.liveu.tv:10020" (remotecontrol/connection.py:22). Modem ID on which unit trying to establish connection with hub. """

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:Next (.+?) hub URL",
                                             "   Attempted to connect to hub on" + CVIOLET + " {0!s}" + CEND)

    def connectedToHubUnit(self, line, filename):
        """ Match after following line (example): INFO:Modem connected: Creator: 6, connected: True, connection: <remotecontrol.connection.Connection instance at 0x75c67b70> (remotecontrol/statemachine.py:56). Connection with hub established over the modem ID. """

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:Modem connected: Creator: (\d+), connected: True, connection:",
                                             CGREEN + "   Successfully connected to hub on modem {0!s}" + CEND)

    def interfacesReadyForStreaming(self, line, filename):
        """ Match after following line (example): INFO:found 6 links ready for streaming (streamer/video/modemupdater.py:73). Returns total number of interfaces ready for streaming (during stream only). """

        return self._findPatternWithGroup(line, filename,
                                             r"streamer\s.+INFO:found (\d+) links ready for streaming",
                                             "   Number of interfaces ready for streaming:" + CVIOLET + " {0!s}" + CEND)

    def unitStopCommandFromGui(self, line, filename):
        """ Match after following line (example): INFO:Stop command from the lu100 GUI (lu100gui/bossqueries.py:109)."""

        return self._findPattern(line, filename,
                                  r"Stop command from the lu100 GUI",
                                  CVIOLET + "   Stop command from GUI" + CEND)

    def unitStopCommandFromCentral(self, line, filename):
        """ Match after following line (example): INFO:Stop command from LUCCMD_production_cluster_1_4161_1549597091_fd4c60c7374c7cd6776e1bba9f23c886 (boss100/statemachine/video/commonstreamingstate.py:107)"""

        return self._findPattern(line, filename,
                                  r"boss100.+INFO:Stop command from LUCCMD",
                                  CVIOLET + "   Stop command from LUC" + CEND)

    def unitStartCommandFromCentral(self, line, filename):
        """ Match after following line (example): INFO:Received 'Stream' command from LUCCMD_production_2_673_1934251753_fd4c60c7374c7cd6776e1bba9f23c886 (boss100/video/statemachine/idle.py:48) """

        return self._findPattern(line, filename,
                                  r"boss100.+INFO:Received.+command from LUCCMD",
                                  "   Start command from LUC")

    def unitVideoSkips(self, line, filename):
        """ Match after following line (example): WARNING:Video skip detected delta=40, max=26 (cpp/CentaurusMediaApplication/Video/Capture.h:186) """

        return self._findPattern(line, filename,
                                  r"WARNING:Video skip detected",
                                  "   Video skip detected")

    def unitPacketDroppWarning(self, line, filename):
        """ Match after following line (example): WARNING:Dropped 1 packets of normal or higher priority (../../cpp/StreamerEngine/Bonding/PacketDroppedTrace.h:42)"""

        return self._findPatternWithGroup(line, filename,
                                             r"python\s.+WARNING:Dropped (\d+) packets of normal or higher priority",
                                             "   Number of packets dropped:" + CVIOLET + " {0!s}" + CEND)

    def unitRtpGapInfo(self, line, filename):
        """ Match after following line (example): INFO:RTP gap detected (or first frame): forcing disabled! (streamer/video/forceidrframe.py:36)"""

        return self._findPattern(line, filename,
                                  r"streamer\s.+INFO:RTP gap detected \(or first frame\)\: forcing disabled\!",
                                  "   RTP gap detected (Macroblocks in video output)!")

    def rebootRequestFromGuiOrLuc(self, line, filename):
        """ Match after following line (example): INFO:Rebooting the system: Reboot was requested [sender: <boss100.ipctongue.Reboot instance at 0x75e6ee90>] (common/system/power.py:15) """

        return self._findPattern(line, filename,
                                  r"INFO:Rebooting the system: Reboot was requested",
                                  "Reboot requested (GUI/LUC)")

    def rebootRequestFromMedic(self, line, filename):
        """ Match after following line (example): """

        return self._findPattern(line,
                                  filename,
                                  r"Running seed reboot",
                                  "Reboot requested (Medic)")

    def softwareStartup(self, line, filename):
        """ Match after following line (example): """

        return self._findPattern(line, filename,
                                  r"(?:Initialize eggs configuration for lu100|overlord\s.+INFO:Initializing eggs for product)",
                                  "Software startup - eggs")

    def unitSyslogStartup(self, line, filename):
        """ Match after following line (example): corecard rsyslogd: [origin software="rsyslogd" swVersion="8.9.0" x-pid="263" x-info="http://www.rsyslog.com"] start. """

        return self._findPattern(line, filename,
                                  r"(?:sitara|corecard) rsyslogd: \[origin software=\"rsyslogd\" [^\]]+\] start",
                                  CBLINK + ">>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<" + CEND + "\n" + CBLINK + "                                  >>>>>>>>" + CEND + CGREEN + " Software startup (syslog) " + CEND + CBLINK + "<<<<<<<<" + CEND)

    def unitPowerShutdownRequested(self, line, filename):
        """ Match after following line (example): INFO:Shutting down the system... (common/system/power.py:20). Shutdown request for the unit. """

        return self._findPattern(line, filename,
                                  r"INFO:Shutting down the system\.\.\.",
                                  "Shutdown requested")

    def connectedToHub(self, line, filename):
        """ Match after following line (example): """

        return self._findPattern(line, filename,
                                  r"Remote control: Successfully connected to hub",
                                  CGREEN + "   Successfully connected to hub" + CEND)

    def vicType(self, line, filename):
        """ Match after following line (example): corecard kernel: Kernel command line: console=ttymxc0,115200n8 root=/dev/mmcblk3p1 rootfstype=ext4 rw rootwait ip=off init="" consoleblank=0 vt.cur_default=1 usbethaddr=78:51:0c:00:e2:07 hwrev=B vic_type=AVIC. Returns vic type and hardware revision. """

        return self._findPatternWithGroupOneTwo(line, filename,
                                                 r"kernel:\s.+hwrev\=([a-zA-Z\d]+) vic_type\=([a-zA-Z\d]+)",
                                                 " VIC type: {1!s}  HW rev: {0!s}")

    def vicSoftwareVersionValidation(self, line, filename):
        """ Match after following line (example): INFO:Checking VIC software version: expected 'v3.0.3b12709' vs. actual 'v3.0.3b12709' (monitor/videointerfacecardmonitor.py:163) """

        return self._findPatternWithGroupOneTwo(line, filename,
                                                 r"INFO:Checking VIC software version: expected \'([\d\.\(\)a-zA-Z]+)\' vs\. actual \'([\d\.\(\)a-zA-Z]+)\'",
                                                 "   VIC software version: expected {0!s} actual {1!s}")

    def avicSoftwareVersion(self, line, filename):
        """ Match after following line (example): INFO:AVIC version is: v3.0.3b12709 (avicmediaapplication/aviclogic.py:149) """

        return self._findPatternWithGroup(line, filename,
                                                 r"INFO:AVIC version is: ([\d\.\(\)a-zA-Z]+)",
                                                 "   AVIC software version is: {0!s}")

    def machineModel(self, line, filename):
        """ Match after following line (example): corecard kernel: Machine model: Lu600board based on Freescale i.MX6 Quad """

        return self._findPatternWithGroup(line, filename,
                                                 r"corecard kernel: Machine model: ([\d\.\(\)a-zA-Z]+)",
                                                 " Unit type: {0!s}")

    def vicSerialNumber(self, line, filename):
        """ Match after following line (example): INFO:VIC serial number: HD33180228 (monitor/videointerfacecardmonitor.py:176) """

        return self._findPatternWithGroup(line, filename,
                                                 r"INFO:VIC serial number: ([\d\.\(\)a-zA-Z]+)",
                                                 " VIC Serial Number is: {0!s}")

    def ubiquityConnected(self, line, filename):
        """ Match after following line (example): """

        return self._findPatternWithGroupOneTwo(line, filename,
                                                 r"eaglenest\s.+INFO:([a-zA-Z\d]+): Cable ([a-zA-Z]+) in ubiquiti AP mode",
                                                 CGREEN + "   Ubiquity {1!s} on: {0!s}" + CEND)

    def ubiquityDisconnected(self, line, filename):
        """ Match after following line (example): """

        return self._findPatternWithGroupOneTwo(line, filename,
                                                 r"eaglenest\s.+INFO:([a-zA-Z\d]+): Cable ([a-zA-Z]+) while in ubiquiti AP mode",
                                                 CYELLOW + "   Ubiquity {1!s} from: {0!s}" + CEND)

    def xtenderEthernetConnected(self, line, filename):
        """ Match after following line (example): INFO:Xtender added on 'eth0' (eaglenest/queryhandler.py:259) """

        return self._findPattern(line, filename,
                                  r"eaglenest\s.+INFO:Xtender added on \'[a-zA-Z\d]+\'",
                                  CGREEN + "   xTender connected" + CEND)

    def xtenderEthernetConnectedVersion7(self, line, filename):
        """ Match after following line (example): INFO:xTender of unique ID Boss100_drone_1d300006265e5a010000000001005e39 was connected on eth1 (xtender/agent/agent.py:30) """

        return self._findPatternWithGroupOneTwo(line, filename,
                                  r"INFO:xTender of unique ID ([^\s]+) was connected on eth(\d+)",
                                  CGREEN + "   xTender connected on eth{1!s}; xTender ID: {0!s}" + CEND)

    def xtenderEthernetDisconnected(self, line, filename):
        """ Match after following line (example): INFO:Xtender on 'eth0' removed (eaglenest/queryhandler.py:255)"""

        return self._findPattern(line, filename,
                                  r"eaglenest\s.+INFO:Xtender on \'[a-zA-Z\d]+\' removed",
                                  CYELLOW + "   xTender disconnected" + CEND)

    def xtenderEthernetDisconnectedVersion7(self, line, filename):
        """ Match after following line (example): INFO:xTender Boss100_drone_1d300006265e5a010000000001005e39 disconnected from eth1 (xtender/agent/agent.py:99) """

        return self._findPatternWithGroupOneTwo(line, filename,
                                  r"INFO:xTender ([^\s]+) disconnected from eth(\d+)",
                                  CYELLOW + "   xTender disconnected from eth{1!s}; xTender ID: {0!s}" + CEND)

    def streamToChannelBossId(self, line, filename):
        """ Match after following line (example): INFO:Collector Started command from Boss1100_21475896183712_Instance1 with version: 6.5.3.C14737.G222dbfa89, collectorAddressList [[u'50.203.95.47', 8610]], previewMode False, ifbAddress: [u'50.203.95.47', 0] (boss100/statemachine/video/startcollector.py:36) """

        return self._findPatternWithGroup(line, filename,
                                             r"boss100.+INFO:Collector Started command from ([^\s]+)",
                                             "   {0!s}")

    def unitBackfireConnectionError(self, line, filename):
        """ Match after following line (example): ERROR:Socket error on recv: Connection refused (cpp/Backfire/Receiver.h:118) """

        return self._findPatternWithGroup(line, filename,
                                             r"ERROR:Socket error on recv: ([^\(]+)",
                                             CRED + "   Received receive socket error: {0!s}!" + CEND)

    def ackReciveWarning(self, line, filename):
        """ Match after following line (example): WARNING:No acks received from streamer for the past 90 seconds (streamer/video/main.py:131) """

        return self._findPatternWithGroup(line, filename,
                                             r"WARNING:No acks received from streamer for the past (\d+) seconds",
                                             CYELLOW + "   No acks received from streamer for the past {0!s} seconds" + CEND)

    def dataReciveInfo(self, line, filename):
        """ Match after following line (example): INFO:No data was received in the past 90 seconds (last packet received at 253040499) (../../cpp/Common/StreamKeepAlive.h:31) """

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:No data was received in the past (\d+) seconds \(last packet received at \d+\)",
                                             CYELLOW + "   No data received in the the past {0!s} seconds!!!" + CEND)

    def unitIncomingDataFlowColectorWarning(self, line, filename):
        """ Match after following line (example): """

        return self._findPattern(line, filename,
                                  r"WARNING:No incoming data flow - maybe MMH stopped collecting",
                                  CYELLOW + "   No incoming data flow - maybe MMH stopped collecting. Stream will STOP!" + CEND)

    def fileTransferSessionComplete(self, line, filename):
        """ Match after following line (example): INFO:File transfer complete, sending to dashboard (../../cpp/StreamerEngine/Applications/FileTransfer/Main.h:81) """

        return self._findPattern(line, filename,
                                  r"python\s.+INFO:File transfer complete, sending to dashboard",
                                  "   File transfer complete")

    def audioCodecResetUnit(self, line, filename):
        """ Match after following line (example): corecard kernel: Warning: SGTL5000 RESET detected !!"""

        return self._findPattern(line, filename,
                                  r"corecard kernel: Warning: SGTL5000 RESET detected !!",
                                  CRED + "   SGTL5000 reset detected! (IFB audio codec)" + CEND)

    def transmitQueueTimeout(self, line, filename):
        """ Match after following line (example): NETDEV WATCHDOG: eth1 (cdc_ether): transmit queue 0 timed out"""

        return self._findPattern(line, filename,
                                  r"NETDEV WATCHDOG: [^\s]+ ([^\s]+): transmit queue 0 timed out",
                                  CRED + "   USB bus reset (4 modem issue)" + CEND)

    def unitPresenterLu100ErrorSystem(self, line, filename):
        """ Match after following line (example): ERROR:Presenter terminated unexpectedly with signal 15 (lu100gui/presenterwatchdog.py:29). Presenter terminated with signal (system). """

        return self._findPatternWithGroup(line, filename,
                                             r"ERROR:Presenter terminated unexpectedly with signal ([^\s]+)",
                                             CRED + "   CRASH! Presenter (GUI) terminated unexpectedly, signal {0!s} (system)!" + CEND)

    def unitPresenterLu100ErrorSoftware(self, line, filename):
        """ Match after following line (example): ERROR:Presenter terminated unexpectedly with exit code 15 (lu100gui/presenterwatchdog.py:29) """

        return self._findPatternWithGroup(line, filename,
                                             r"ERROR:Presenter terminated unexpectedly with exit code ([^\s]+)",
                                             CRED + "   CRASH! Presenter (GUI) terminated unexpectedly, exit code {0!s} (software)!" + CEND)

    def memoryVicWarning(self, line, filename):
        """ Match after following line (example): WARNING:Memory usage is 95.7% (monitor/memorymonitor.py:35) """

        return self._findPatternWithGroup(line, filename,
                                             r"vic monitor.+WARNING:Memory usage is too high: ([^\(]+)",
                                             CYELLOW + "   VIC: {0!s} !" + CEND)

    def memoryCorecardWarning(self, line, filename):
        """ Match after following line (example): WARNING:Memory usage is 95.7% (monitor/memorymonitor.py:35) """

        return self._findPatternWithGroup(line, filename,
                                             r"corecard monitor.+WARNING:Memory usage is too high: ([^\(]+)",
                                             CYELLOW + "   COR: {0!s} !" + CEND)

    def memoryVicInfo(self, line, filename):
        """ Match after following line (example): INFO:Memory usage is 25.7% (531 MB out of 2069 MB), cached - 145 MB (monitor/memorymonitor.py:32) """

        return self._findPatternWithGroup(line, filename,
                                             r"vic monitor.+INFO:Memory usage is ([^\(]+)",
                                             "   VIC: {0!s}")

    def memoryCorecardInfo(self, line, filename):
        """ Match after following line (example): INFO:Memory usage is 25.7% (531 MB out of 2069 MB), cached - 145 MB (monitor/memorymonitor.py:32) """

        return self._findPatternWithGroup(line, filename,
                                             r"corecard monitor.+INFO:Memory usage is ([^\(]+)",
                                             "   COR: {0!s}")

    def cpuCorecardInfo(self, line, filename):
        """ Match after following line (example): INFO:CPU usage in detail is scputimes(user=7.0999999999999996, nice=0.0, system=5.2999999999999998, idle=86.5, iowait=1.0, irq=0.0, softirq=0.0, steal=0.0, guest=0.0, guest_nice=0.0) (monitor/cpumonitor.py:62) """

        return self._findPatternWithGroup(line, filename,
                                             r"corecard monitor.+INFO:CPU usage in detail is scputimes.+idle=([^\,]+)",
                                             "   COR IDLE: {0!s}")

    def cpuVicInfo(self, line, filename):
        """ Match after following line (example): INFO:CPU usage in detail is scputimes(user=7.0999999999999996, nice=0.0, system=5.2999999999999998, idle=86.5, iowait=1.0, irq=0.0, softirq=0.0, steal=0.0, guest=0.0, guest_nice=0.0) (monitor/cpumonitor.py:62) """

        return self._findPatternWithGroup(line, filename,
                                             r"vic monitor.+INFO:CPU usage in detail is scputimes.+idle=([^\,]+)",
                                             "   VIC IDLE: {0!s}")

    def cpuCorecardWarning(self, line, filename):
        """ Match after following line (example): """

        return self._findPatternWithGroup(line, filename,
                                             r"corecard monitor.+WARNING:CPU usage in detail is scputimes.+idle=([^\,]+)",
                                             CYELLOW + "   COR IDLE: {0!s} !" + CEND)

    def cpuVicWarning(self, line, filename):
        """ Match after following line (example): """

        return self._findPatternWithGroup(line, filename,
                                             r"vic monitor.+WARNING:CPU usage in detail is scputimes.+idle=([^\,]+)",
                                             CYELLOW + "   VIC IDLE: {0!s} !" + CEND)

    def cpuCorecardWarningVersion7(self, line, filename):
        """ Match after following line (example): WARNING:CPU utilization on core 3 (index starts from 0) is high: scputimes(user=1.0, nice=84.700000000000003, system=0.0, idle=14.300000000000001, iowait=0.0, irq=0.0, softirq=0.0, steal=0.0, guest=0.0, guest_nice=0.0) (monitor/warningreceiver.py:20) """

        return self._findPatternWithGroupOneTwo(line, filename,
                                             r"corecard monitor.+WARNING:CPU utilization on core (\d+) \(index starts from \d+\) is high:.+idle=([^\,]+)",
                                             CYELLOW + "   CORCARD CPU CORE {0!s} IDLE: {1!s} !" + CEND)

    def cpuVicWarningVersion7(self, line, filename):
        """ Match after following line (example): WARNING:CPU utilization on core 3 (index starts from 0) is high: scputimes(user=1.0, nice=84.700000000000003, system=0.0, idle=14.300000000000001, iowait=0.0, irq=0.0, softirq=0.0, steal=0.0, guest=0.0, guest_nice=0.0) (monitor/warningreceiver.py:20) """

        return self._findPatternWithGroupOneTwo(line, filename,
                                             r"vic monitor.+WARNING:CPU utilization on core (\d+) \(index starts from \d+\) is high:.+idle=([^\,]+)",
                                             CYELLOW + "   VIC CPU CORE {0!s} IDLE: {0!s} !" + CEND)

    def modemGradingLimitedServiceRttValues(self, line, filename):
        """ Match after following line (example): INFO:modem 3 extrapolated smooth rtt (572) or upstreamdelay (560) NOT good enough for full service (../../cpp/StreamerEngine/ModemGrading/ModemGrading.h:202) """

        return self._findPatternWithGroupOneTwoThree(line, filename,
                                                   r"INFO:modem (\d+) extrapolated smooth rtt \((\d+)\) or upstreamdelay \((\d+)\) NOT good enough for full service",
                                                   "   ModemID\t{0!s}\t{1!s}\t{2!s}\tNot good enough for full service")

    def modemGradingLimitedService(self, line, filename):
        """ Match after following line (example): INFO:ModemGrading: changed grade of modem 3 from Full Service to Limited Service (../../cpp/StreamerEngine/ModemGrading/ModemGrading.h:196)"""

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:ModemGrading: changed grade of modem (\d+) from Full Service to Limited Service",
                                             "   ModemID\t{0!s}\tLimited Service")

    def modemGradingLimitedServiceLossValue(self, line, filename):
        """ Match after following line (example): INFO:modem 4 loss ( 46 ) above full service ceil 25 (../../cpp/StreamerEngine/ModemGrading/ModemGrading.h:212)"""

        return self._findPatternWithGroupOneTwoThree(line, filename,
                                                   r"INFO:modem (\d+) loss \( (\d+) \) above full service ceil (\d+)",
                                                   "   ModemID\t{0!s}\t{1!s}\t{2!s}\tNot good enough for full service\n")

    def modemGradingFullServiceRttValues(self, line, filename):
        """ Match after following line (example): INFO:modem 10 extrapolated smooth rtt (130) or extrapolated upstreamdelay (77) good enough for full service (../../cpp/StreamerEngine/ModemGrading/ModemGrading.h:205) """

        return self._findPatternWithGroupOneTwoThree(line, filename,
                                                   r"INFO:modem (\d+) extrapolated smooth rtt \((\d+)\) or extrapolated upstreamdelay \((\d+)\) good enough for full service",
                                                   "   ModemID\t{0!s}\t{1!s}\t{2!s}\tGood enough for full service")

    def modemGradingFullService(self, line, filename):
        """ Match after following line (example): INFO:ModemGrading: changed grade of modem 8 from Limited Service to Full Service (../../cpp/StreamerEngine/ModemGrading/ModemGrading.h:194)"""

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:ModemGrading: changed grade of modem (\d+) from Limited Service to Full Service",
                                             "   ModemID\t{0!s}\tFull Service")

    def modemGradingFullServiceLossValue(self, line, filename):
        """ Match after following line (example): INFO:modem 4 loss ( 0 ) below limited service floor 20 (../../cpp/StreamerEngine/ModemGrading/ModemGrading.h:217)"""

        return self._findPatternWithGroupOneTwoThree(line, filename,
                                                   r"INFO:modem (\d+) loss \( (\d+) \) below limited service floor (\d+)",
                                                   "   ModemID\t{0!s}\t{1!s}\t{2!s}\tGood enough for full service\n")

    def socketAddressWarningEggAlreadyStarted(self, line, filename):
        """ Match after following line (example): WARNING:Constellation already holds egg master_directstreamer (overlord/master/constellation.py:49) """

        return self._findPatternWithGroup(line, filename,
                                             r"WARNING:Constellation already holds egg ([^\s]+)",
                                             CYELLOW + "   WARNING! Constelation already holds egg {0!s} (Socket, address already in use)!" + CEND)

    def totalBandwidthLow(self, line, filename):
        """ Match after following line (example): INFO:Total bandwidth is low: 87 kbps (cpp/StreamerEngine/CongestionMonitor/FullServiceBandwidth.h:50) """

        pat = r"Total bandwidth is low: (\d+) kbps"
        match = re.search(pat, line.raw)
        if match:
            bandwidth = int(match.group(1))
            if bandwidth > 0 and bandwidth < 300:
                self._print(line.datetime, (CYELLOW + "    Total bandwidth is low: {0!s} kbps!" + CEND).format(bandwidth), filename)
                return True
        return False

    def remoteControlActiveConnectionNumber(self, line, filename):
        """ Match after following line (example): """

        pat = r"Socket got disconnected: Creator: \d\, connected: False\, connection: None \(connected count: (\d+)\)"
        match = re.search(pat, line.raw)
        if match:
            connections = int(match.group(1))
            if connections > 0:
                self._print(line.datetime, "   Remaining active connections with hub: {0!s}".format(connections), filename)
                return True
        return False

    def soloFfmpegCrashError(self, line, filename):
        """ Match after following line (example): """

        return self._findPattern(line, filename,
                                  r"directstreamer.+ERROR:FFMEPEG command stopped unexpectedly for stream",
                                  CRED + "   FFMEPEG stopped unexpectedly!" + CEND)

    def soloFfmpegCrashErrorVersion7(self, line, filename):
        """ Match after following line (example): ERROR:FFMEPEG command stopped unexpectedly for Stream (common/ffmpegwatchdog.py:9)"""

        return self._findPattern(line, filename,
                                  r"directstreamer.+ERROR:FFMEPEG command stopped unexpectedly for Stream",
                                  CRED + "   FFMEPEG stopped unexpectedly!" + CEND)

# Unit databridge mode

    def streamSessionStartDataBridge(self, line, filename):
        """ Match after following line (example): INFO:Entering state "StartDatabridgeStreamer" with args: (), {'lu1100ID': u'Boss1100_DB_7484218211886_Instance1', 'pepEnabled': u'False', 'pipelineType': {'type': 'transparentBridge'}, 'collectorAddress': ([u'54.229.210.63'], 9000)} (common/statemachine/state.py:21) """

        did_match = self._findPatternWithGroup(line, filename,
                                                  r"Entering state \"StartDatabridgeStreamer\" with args: \(\).+'collectorAddress'\: \(\[u?'([\d\.]+)'\], \d+\)",
                                                  "<~~ DB stream start to IP: {0!s} (Gateway)")
        if did_match:
            SessionTracker.instance().logStart(line.datetime)
        return did_match

    def streamSessionEndDataBridge(self, line, filename):
        """ Match after following line (example): INFO:Entering state "StopCollectorAndStreamer" with args: (), {} (common/statemachine/state.py:21)"""

        did_match = self._findPattern(line, filename,
                                       r"Entering state \"StopCollectorAndStreamer\"",
                                       "~~> DB stream end (Gateway)")
        if did_match:
            SessionTracker.instance().logEnd(line.datetime)
        return did_match

    def streamSessionStartDataBridgeMultiPath(self, line, filename):
        """ Match after following line (example): """

        did_match = self._findPattern(line, filename,
                                       r"Entering state \"MultiWANRouter\" with args:",
                                       "<~~ DB stream start (Multipath)")
        if did_match:
            SessionTracker.instance().logStart(line.datetime)
        return did_match

    def streamSessionEndDataBridgeMultiPath(self, line, filename):
        """ Match after following line (example): """

        did_match = self._findPattern(line, filename,
                                       r"Entering state \"MultiWANRouterStopping\"",
                                       "~~> DB stream end (Multipath)")
        if did_match:
            SessionTracker.instance().logEnd(line.datetime)
        return did_match

    def gatewayChannelAllocated(self, line, filename):
        """ Match after following line (example): INFO:collector started command from Boss1100_DB_7484218211886_Instance1 NAT mode: False (boss100/statemachine/databridge/startdatabridgecollector.py:42)"""

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:collector started command from ([^\s]+)",
                                             "<~~ Databridge channel ID: {0!s}")

    def dataBrdgeCollectorCrashError(self, line, filename):
        """ Match after following line (example): INFO:collector stopped (unexpectedly) command from Boss1100_DB_6749769207452_Instance3. Stopping stream. (boss100/statemachine/databridge/transparentbridge.py:37) """

        return self._findPattern(line, filename,
                                  r"INFO:collector stopped \(unexpectedly\)",
                                  "   Gateway collector stopped unexpectedly - Stream will STOP!")

    def switchingFromVideoToDataBridgeMode(self, line, filename):
        """ Match after following line (example): INFO:Received 'TransparentBridge' command  (boss100/statemachine/idle.py:99) """

        return self._findPattern(line, filename,
                                  r"INFO:Received \'TransparentBridge\' command",
                                  "   Switching to data bridge mode...")

    def ethernetLinkUpDownUnit(self, line, filename):
        """ Match after following line (example): corecard kernel: [  396.713836] ETH LINK UP INTERRUPT RECEVIED."""

        return self._findPatternWithGroup(line, filename,
                                             r"ETH LINK ([a-zA-Z]+) INTERRUPT RECEVIED\.",
                                             "   ETHERNET LINK IS {0!s}")

    def onlineOfflineDuringLiveSessionDataBridge(self, line, filename):
        """ Match after following line (example): """

        return self._findPatternWithGroup(line, filename,
                                             r"ERROR:Illegal event \"([a-zA-Z]+)\" in state \"SetupBridgeAndStreamerInterfaceIPForwarding\"",
                                             "   Unit got" + CBLINK + " {0!s}" + CEND + " event while still streaming, it was {0!s} in LUC")

    def onlineOfflineWhileStartingCollectorDataBridge(self, line, filename):
        """ Match after following line (example): """

        return self._findPatternWithGroup(line, filename,
                                             r"ERROR:Illegal event \"([a-zA-Z]+)\" in state \"StartDatabridgeCollector\"",
                                             "   Unit got " + CBLINK + " {0!s}" + CEND + " event while starting db collector, it was {0!s} in LUC")

    def dhcpFailedDataBridge(self, line, filename):
        """ Match after following line (example): corecard stderr: Exception AttributeError: "'NoneType' object has no attribute 'close'" in <bound method Layer3Forwarder.__del__ of <eaglenest.databridge.layer3forwarder.Layer3Forwarder instance at 0x75f2b170>> ignored """

        return self._findPattern(line, filename,
                                  r"Exception AttributeError: \"\'NoneType\' object has no attribute \'close\'\" in \<bound method Layer3Forwarder",
                                  CRED + "   Ethernet interface failed to get IP address from gateway (dhcp), maybe due to offline state - Stream will STOP!" + CEND)

    def dhcpAttemptDataBridge(self, line, filename):
        """ Match after following line (example): ERROR:Failed to get dhcp from server (common/retry.py:18) """

        return self._findPattern(line, filename,
                                  r"ERROR:Failed to get dhcp from server",
                                  "   Attempted to get IP address from gateway (dhcp)")

    def dhcpObtainedDataBridge(self, line, filename):
        """ Match after following line (example): INFO:Entered state "TransparentBridge" (common/statemachine/state.py:23)"""

        return self._findPattern(line, filename,
                                  r"INFO:Entered state \"TransparentBridge\"",
                                  CGREEN + "   IP address obtained from gateway (dhcp)" + CEND)

    def timeoutWaitingForCollectorToStartDataBridge(self, line, filename):
        """ Match after following line (example): """

        return self._findPattern(line, filename,
                                  r"boss100.+WARNING:Timeout while waiting for collector on to start. Telling collector to stop",
                                  CYELLOW + "   Timeout waiting for collector to start (colector stopped)" + CEND)

    def startCollectorDataBridge(self, line, filename):
        """ Match after following line (example): INFO:Entered state "StartDatabridgeCollector" (common/statemachine/state.py:23) """

        return self._findPattern(line, filename,
                                  r"boss100.+INFO:Entered state \"StartDatabridgeCollector\"",
                                  "   Starting data bridge collector > > >")

# MMH server

    def serviceLiveuStart(self, line, filename):
        """ Match after following line (example): INFO:SignalBus is ready to handle requests (signalbus/main.py:25) """

        return self._findPattern(line, filename,
                                  r"signalbus.+INFO:SignalBus is ready to handle requests",
                                  CGREEN + ">>>> LiveU service started (signalbus) <<<<" + CEND)

    def whoIsStreamingToThisChannel(self, line, filename):
        """ Match after following line (example): INFO:Received 'Initiation Request' from: Boss100_20c0001899876301000000100100ce2a with version: 6.0.1.C11785.G9e7290f04 and capabilities: [u'ifb', u'previewMode', u'earlyGapDetection', {u'audioChannels': [2]}]. Sending 'Initiation Response' (boss1100/video/statemachine/idle.py:34) """

        return self._findPatternWithGroup(line, filename,
                                             r"Received 'Initiation Request' from: ([^\s]+ with version: [^\s]+)",
                                             "   Stream requested from: {0!s}")

    def blackMagicCardSoftwareVersion(self, line, filename):
        """ Match after following line (example): INFO:Using blackmagic SDK version 10.1.4 (cpp/Blackmagic/CardIterator.h:16) """

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:Using blackmagic SDK version ([^\s]+)",
                                             "   Blackmagic driver version is: {0!s}")

    def audioOutputTypeTwoChannels(self, line, filename):
        """ Match after following line (example): INFO:Starting audio output callback with 2 channels. Pre rolling 10240 audio samples (cpp/Blackmagic/Render/Audio/OutputCallback.h:32) """

        return self._findPattern(line, filename,
                                  r"INFO:Starting audio output callback with 2 channels\.",
                                  "   Audio output type was: 2 channels")

    def audioOutputTypeFourChannels(self, line, filename):
        """ Match after following line (example): """

        return self._findPattern(line, filename,
                                  r"INFO:Starting audio output callback with 8 channels\.",
                                  "   Audio output type was: 4 channels")

    def hubConnectAttemptServer(self, line, filename):
        """ Match after following line (example): INFO:Next hub URL "ws://hub1.liveu.tv:10020" (remotecontrol/connection.py:24) """

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:Next hub URL \"(.+?)\"",
                                             "   Attempted to connect to hub:" + CVIOLET + " {0!s}" + CEND)

    def connectedToHubServer(self, line, filename):
        """ Match after following line (example): INFO:Modem connected: Creator: default, connected: True, connection: <remotecontrol.connection.Connection instance at 0x2d50320> (remotecontrol/statemachine.py:56)"""

        return self._findPattern(line, filename,
                                  r"INFO:Modem connected: Creator: default, connected: True, connection:",
                                  CGREEN + "   Successfully connected to hub" + CEND)

    def serverUpgradeError(self, line, filename):
        """ Match after following line (example): """

        return self._findPattern(line, filename,
                                  r"stderr: ssh: connect to host rsync\.liveu\.tv port 22222: Connection timed out#015",
                                  CRED + "   Error: Upgrade failed, port 22222 was closed" + CEND)

    def multimediaTransformerCrashError(self, line, filename):
        return self._findPatternWithGroup(line, filename,
                                             r"ERROR:Multimedia Transformers forwarding stopped unexpectedly with exit code ([^\s]+)",
                                             CRED + "   Multimedia Transformers CRASH!, exit code {0!s}" + CEND)

    def streamingUnitBossId(self, line, filename):
        """ Match after following line (example): """

        return self._findPatternWithGroup(line, filename,
                                             r"boss1100.+INFO:Received start collector command from ([^\s]+)",
                                             "   {0!s}")

    def serverBackfireConnectionError(self, line, filename):
        """ Match after following line (example): """

        return self._findPattern(line, filename,
                                  r"ERROR:Receive reports socket was closed",
                                  CRED + "   Receive reports socket was closed - Stream will STOP!" + CEND)

    def stopStreamCommandFromInfo(self, line, filename):
        """ Match after following line (example): INFO:Received 'Stop' command from Boss100_0f900001f2dd6301000000100100ca0e (boss1100/video/statemachine/commoncollectorrunningstate.py:45)"""

        return self._findPatternWithGroup(line, filename,
                                             r"boss1100.+INFO:Received 'Stop' command from ([^\(]+)",
                                             "   Received 'STOP' command from {0!s}")

    def unitOfflineDuringCollectingSession(self, line, filename):
        """ Match after following line (example): INFO:Device Boss100_2590011888a05701000000000100ec52 went offline (boss1100/video/statemachine/collecting.py:77) """

        return self._findPatternWithGroup(line, filename,
                                             r"boss1100.+INFO:Device ([^\s]+) went offline ",
                                             CYELLOW + "   Device {0!s} went offline (device/server offline in LUC, device rebooted...)" + CEND)
    def streamAtVideoGatewayFailedToStart(self, line, filename):
        """ Match after following line (example): ERROR:Error starting stream at Video Gateway: timed out (boss1100/actions.py:95) """

        return self._findPattern(line, filename,
                                             r"boss1100.+ERROR:Error starting stream at Video Gateway:",
                                             CRED + "   Error starting stream at Video Gateway !" + CEND)
    def modemconfigurationCorrupted(self, line, filename):
        """ Match after following line (example): ERROR:Failed to evaluate modemconfiguration: /settings/modemconfiguration.txt, error: unexpected EOF while parsing (<string>, line 0), using empty configuration (eaglenest/modemconfiguration.py:158) """

        return self._findPattern(line, filename,
                                             r"ERROR:Failed to evaluate modemconfiguration: /settings/modemconfiguration.txt, error:",
                                             CRED + "   Error modemconfiguration.txt file got corrupted !" + CEND)

    def unitOnlineDuringCollectingSession(self, line, filename):
        """ Match after following line (example): INFO:Device Boss100_0a30010c114f6801000000000100ec53 came back online, collecting... (boss1100/video/statemachine/collecting.py:79) """

        return self._findPatternWithGroup(line, filename,
                                             r"boss1100.+INFO:Device ([^\s]+) came back online, collecting\.\.\.",
                                             CGREEN + "   Device {0!s} came back online" + CEND)

    def collectorStoppingDueToIdleStateOfTheDevice(self, line, filename):
        """ Match after following line (example): INFO:Streaming device is idle. Assuming stopped, and stopping collector (boss1100/video/statemachine/collecting.py:69) """

        return self._findPattern(line, filename,
                                  r"boss1100.+INFO:Streaming device is idle. Assuming stopped, and stopping collector",
                                  CYELLOW + "   Streaming device is in IDLE mode. Assuming stopped - Stoping collector, stream will STOP!" + CEND)

    def videoRtpPacketsOutOfSequenceServer(self, line, filename):
        """ Match after following line (example): ERROR:Video (0): 53 RTP packets were out of sequence in the last 2 seconds (cpp/CollectorEngine/RTPGapReporter.h:45)"""

        pat = r"Video \(\d\): (\d+) RTP packets were out of sequence in the last \d seconds"
        match = re.search(pat, line.raw)
        if match:
            lost_number = int(match.group(1))
            if lost_number > 50 and lost_number < 65000:
                self._print(line.datetime, (CYELLOW + "   Large number of video RTP packets lost: {0!s}" + CEND).format(lost_number), filename)
                return True
        return False

    def audioRtpPacketsOutOfSequenceServer(self, line, filename):
        """ Match after following line (example): ERROR:Audio (1): 10944 RTP packets were out of sequence in the last 2 seconds (collector/rtpgapsreporter.py:63) """

        pat = r"Audio \(\d\): (\d+) RTP packets were out of sequence in the last \d seconds"
        match = re.search(pat, line.raw)
        if match:
            lost_number = int(match.group(1))
            if lost_number > 50 and lost_number < 65000:
                self._print(line.datetime, (CYELLOW + "   Large number of audio RTP packets lost: {0!s}" + CEND).format(lost_number), filename)
                return True
        return False

    def frameErrorWarningServer(self, line, filename):
        """ Match after following line (example): WARNING:Received frame error number -56 frame timestamp 59678902 (cpp/Multimedia/Video/Player.h:210) """

        return self._findPattern(line, filename,
                                  r"WARNING:Received frame error number -(51|56) frame timestamp (\d+)",
                                  CYELLOW + "   Frame error received (RTP gap macroblocks in video output)!" + CEND)

    def decodingFrameErrorServer(self, line, filename):
        """ Match after following line (example): WARNING:Decoding frame error number -59 (cpp/Vanguard/DecoderHandle.h:48)"""

        return self._findPatternWithGroup(line, filename,
                                             r"multimediatransformers\.bin.+WARNING:Decoding frame error number ([^\s]+)",
                                             CYELLOW + "   Decoding frame error received {0!s} (macroblocks in video output)!" + CEND)

    # def mmh_streamstart(self, line, filename):
        # did_match = self._findPattern(line, filename,
                                         # r"Entering state \"Collecting\"",
                                         # "<~~ Stream start (Collecting)")
        # if did_match:
            # SessionTracker.instance().logStart(line.datetime)
        # return did_match

    def streamSessionStartServer(self, line, filename):
        """ Match after following line (example): INFO:Entered state "CollectorStarting" (common/statemachine/state.py:23)"""

        did_match = self._findPattern(line, filename,
                                       r"Entered state \"CollectorStarting\"",
                                       "<~~ Stream start (Collecting)")
        if did_match:
            SessionTracker.instance().logStart(line.datetime)
        return did_match

    def streamSessionEndServer(self, line, filename):
        """ Match after following line (example): INFO:Entering state "CollectorStopping" with args: ('Collector stopped receiving data', True), {} (common/statemachine/state.py:21) """

        did_match = self._findPattern(line, filename,
                                       r"Entering state \"CollectorStopping\"",
                                       "~~> Stream stop (Collecting)")
        if did_match:
            SessionTracker.instance().logEnd(line.datetime)
        return did_match

    def symanticSesssionId(self, line, filename):
        """ Match after following line (example): INFO:Allocate SESSION ID: 6319776 (boss100/statemachine/video/selectchannel.py:47) INFO:Received SESSION ID: 6319776 from Boss1100_189250940225328_Instance2  (boss100/statemachine/video/selectchannel.py:53)"""

        did_match = self._findPatternWithGroup(line, filename,
                                                  r"INFO:(?:Allocate|Received) SESSION ID:\s+(\d+)\s+",
                                                  "   Session id:" + CVIOLET + " {0!s}" + CEND)
        if did_match:
            SessionTracker.instance().logSessionId(did_match.group(1))

    def playFileToSdiSessionStartServer(self, line, filename):
        """ Match after following line (example): INFO:Play stored file ( /var/opt/liveu/fileserver_instance3/filetransfers/201718-24163/BSP-BILHA+CC_180926_181343.mkv ) command from LUCCMD_production_2_1177_2019502615_fd4c60c7374c7cd6776e1bba9f23c886 (boss1100/video/statemachine/idle.py:59) """

        return self._findPattern(line, filename,
                                  r"boss1100.+INFO:Play stored file.+command from LUCCMD",
                                  "<~~ Play file start (from LUC)")

    def playFileToSdiSessionEndServer(self, line, filename):
        """ Match after following line (example): INFO:Stop command from LUCCMD_production_1_1810_2045542821_fd4c60c7374c7cd6776e1bba9f23c886 (boss1100/video/statemachine/playstoredfile.py:37)"""

        return self._findPattern(line, filename,
                                  r"boss1100.+INFO:Stop command from LUCCMD",
                                  "~~> Stop command from LUC")

    def unitStoppingStreamCollectorStopped(self, line, filename):
        """ Match after following line (example): ERROR:Collector stopped (unexpectedly) command from Boss1100_189250943573395_Instance1. Stopping stream. (boss100/statemachine/video/commonstreamingstate.py:135) """

        return self._findPattern(line, filename,
                                  r"boss100\s.+ERROR:Collector stopped \(unexpectedly\)",
                                  CRED + "   MMH collector stopped unexpectedly - Stream will STOP!" + CEND)

    def serverCollectorStoppedReceivingData(self, line, filename):
        """ Match after following line (example): WARNING:Collector stopped receiving data - stopping (boss1100/video/statemachine/commoncollectorrunningstate.py:82) """

        return self._findPattern(line, filename,
                                  r"boss1100.+WARNING:Collector stopped receiving data - stopping",
                                  CRED + "   MMH collector stopped stopped receiving data - Stream will STOP!" + CEND)

    def memoryServerWarning(self, line, filename):
        """ Match after following line (example): WARNING:Memory usage is too high: 99.51 % (monitor/warningreceiver.py:15) """

        return self._findPatternWithGroup(line, filename,
                                             r"monitor\[.+WARNING:Memory usage is too high: ([^\(]+)",
                                             CYELLOW + "   {0!s} !" + CEND)

    def memoryServerInfo(self, line, filename):
        """ Match after following line (example): INFO:Memory usage is 46.2% (3767 MB out of 8150 MB), cached - 2604 MB (monitor/memorymonitor.py:31) """

        return self._findPatternWithGroup(line, filename,
                                             r"monitor\[.+INFO:Memory usage is ([^\(]+)",
                                             "   {0!s}")

    def cpuServerInfo(self, line, filename):
        """ Match after following line (example): INFO:CPU usage is at 29.200% (monitor/cpumonitor.py:65)"""

        return self._findPatternWithGroup(line, filename,
                                             r"monitor\[.+INFO:CPU usage is at ([^\(]+)",
                                             "   {0!s}")

    def cpuServerWarning(self, line, filename):
        """ Match after following line (example): WARNING:CPU usage is at 100.000% (monitor/warningreceiver.py:25) """

        return self._findPatternWithGroup(line, filename,
                                             r"monitor\[.+WARNING:CPU usage is at ([^\(]+)",
                                             CYELLOW + "   {0!s} !" + CEND)

    def cpuServerWarningVersion7(self, line, filename):
        """ Match after following line (example): WARNING:CPU utilization on core 3 (index starts from 0) is high: scputimes(user=1.0, nice=84.700000000000003, system=0.0, idle=14.300000000000001, iowait=0.0, irq=0.0, softirq=0.0, steal=0.0, guest=0.0, guest_nice=0.0) (monitor/warningreceiver.py:20) """

        return self._findPatternWithGroupOneTwo(line, filename,
                                             r"monitor\[.+WARNING:CPU utilization on core (\d+) \(index starts from \d+\) is high:.+idle=([^\,]+)",
                                             CYELLOW + "   CPU CORE {0!s} IDLE: {1!s} !" + CEND)

    def peerListInterfacesAdd(self, line, filename):
        """ Match after following line (example): INFO:Peer added ipaddr: 166.172.184.138, port: 23684 (static no, descriptor 10) (../../cpp/CollectorEngine/PeerList.h:90) """

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:Peer added ipaddr: ([^\(]+)",
                                             CGREEN + "   Peer added ipaddr: {0!s}" + CEND)

    def peerListInterfacesRemove(self, line, filename):
        """ Match after following line (example): INFO:Peer: 166.172.187.41 port 18702 became stale, removing (../../cpp/CollectorEngine/PeerList.h:49) """

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:Peer: ([^\(]+)",
                                             CYELLOW + "   Peer ipaddr {0!s}" + CEND)

# P2MP

    def p2mpStreamStart(self, line, filename):
        """ Match after following line (example): INFO:P2MP device 3 Idle. Streaming... (p2mp/device/device.py:120) """

        return self._findPatternWithGroup(line, filename,
                                             r"INFO:P2MP device (\d+) Idle\. Streaming\.\.\.",
                                             "   P2MP device {0!s} stream started")

    def p2mpStreamStop(self, line, filename):
        """ Match after following line (example): INFO:Device 3 control thread terminated (p2mp/device/device.py:68) """

        return self._findPatternWithGroup(line, filename,
                                             r"videogateway.+INFO:Device (\d+) control thread terminated",
                                             "   P2MP device {0!s} stream stopped, control thread terminated")

    def p2mpAddingSubscriber(self, line, filename):
        """ Match after following line (example): INFO:Adding virtual device <videogateway.mediaoutput.p2mpmediaoutput.P2mpMediaOutput object at 0x7ff738160a10> (p2mp/manager/manager.py:70) """

        return self._findPattern(line, filename,
                                  r"videogateway.+INFO:Adding virtual device",
                                  "   P2MP adding new virtual device (LUC)")

    def p2mpRemovingSubscriber(self, line, filename):
        """ Match after following line (example): INFO:Removing virtual device with ID Boss1100_14038013210062_Instance4 (p2mp/manager/manager.py:78) """

        return self._findPattern(line, filename,
                                  r"videogateway.+INFO:Removing virtual device with ID",
                                  "   P2MP removing virtual device (LUC)")

    def p2mpMultimediaDistributerError(self, line, filename):
        """ Match after following line (example): ERROR:Multimedia Distributer forwarding stopped unexpectedly with exit code -11 (videogateway/multimediadistributerwatchdog.py:44)"""

        return self._findPatternWithGroup(line, filename,
                                             r"videogateway.+ERROR:Multimedia Distributer forwarding stopped unexpectedly with exit code ([^\s]+)",
                                             CRED + "   Multimedia Distributer CRASH!, exit code {0!s}" + CEND)

# Databridge GW

    def timeoutWaitingStartStreamingDataBridge(self, line, filename):
        """ Match after following line (example): WARNING:Timeout while waiting for device to start streaming. Halting collection, informing device (boss1100/video/statemachine/collectorstarting.py:88) """

        return self._findPattern(line, filename,
                                  r"WARNING:Timeout while waiting for device to start streaming. Halting collection, informing device",
                                  CYELLOW + "   Timeout while waiting for device to start stream. Collector will STOP (unit might be offline)!" + CEND)

    def hubConnectionTimeoutDataBridgeGateway(self, line, filename):
        """ Match after following line (example): ERROR:Delay on remote control link (default) is above 12, removing connection (remotecontrol/pingpong.py:23) """

        return self._findPattern(line, filename,
                                  r"ERROR:Delay on remote control link \(default\) is above 12, removing connection",
                                  CYELLOW + "   Hub connection timeout, delay was above 12, removing connection" + CEND)

    def offlineDuringCollectingGwDataBridge(self, line, filename):
        """ Match after following line (example): INFO:HUB is offline (boss1100/databridge/statemachine/collecting.py:54) """

        return self._findPattern(line, filename,
                                  r"INFO:HUB is offline",
                                  CYELLOW + "   Gateway got offline event while still in collecting, it was offline in LUC" + CEND)

    def process(self, line, filename):
        # first insure the line is even in our date range:
        log_line = None
        decoded = False
        try:
            log_line = LogLine(line, self.timezone)
            decoded = True
        except UnicodeDecodeError:
            pass

        if decoded:
            if self.daterange.existIn(log_line.datetime):
                if self.parse_type == 'known':
                    self.known(log_line, filename)
                elif self.parse_type == 'v':
                    self.verbose(log_line, filename)
                elif self.parse_type == 'error':
                    self.error(log_line, filename)
                elif self.parse_type == 'all':
                    self.all(log_line, filename)
                elif self.parse_type == 'bw':
                    self.bw(log_line, filename)
                elif self.parse_type == 'md-bw':
                    self.modem_bw(log_line, filename)
                elif self.parse_type == 'md-db-bw':
                    self.db_modem_bw(log_line, filename)
                elif self.parse_type == 'md':
                    self.modems(log_line, filename)
                elif self.parse_type == 'sessions':
                    self.sessions(log_line, filename)
                elif self.parse_type == 'id':
                    self.id(log_line, filename)
                elif self.parse_type == 'memory':
                    self.memory(log_line, filename)
                elif self.parse_type == 'grading':
                    self.grading(log_line, filename)
                elif self.parse_type == 'cpu':
                    self.cpu(log_line, filename)
                elif self.parse_type == 'debug':
                    self.debug(log_line, filename)
                elif self.parse_type == 'modemevents':
                    self.modemevents(log_line, filename)
                elif self.parse_type == 'modemeventssorted':
                    ConnectivitySummary.instance().on = True
                    self.modemeventssorted(log_line, filename)

    @classmethod
    def print_csv_header(cls):
        print("datetime,total bitrate,video bitrate,notes")

    @classmethod
    def print_csv_md_header(cls):
        print("ModemID\tDate/time\tPotentialBW\tLoss\tExtrapolated smooth upstream\tShortest round trip\tExtrapolated smooth round trip\tMinimum smooth round trip\tNotes")

    def print_csv_md_db_header(cls):
        print("ModemID\tDate/time\tPotentialBW\tLoss\tDelay\tNotes")

    def bw(self, line, filename):
        for processor in self.csv_processors:
            if processor(line, filename):
                break

    def modem_bw(self, line, filename):
        for processor in self.csv_loss_processors:
            if processor(line, filename):
                break

    def db_modem_bw(self, line, filename):
        for processor in self.csv_loss_db_processors:
            if processor(line, filename):
                break

    def known(self, line, filename):
        for processor in self.all_processors:
            if processor(line, filename):
                break

    def error(self, line, filename):
        pat = r"ERROR"
        match = re.search(pat, line.raw)
        if match:
            self._print(line.datetime, line.message, filename)

    def all(self, line, filename):
        self._print(line.datetime, line.message, filename)

    def verbose(self, line, filename):
        for processor in self.verbose_processors:
            if processor(line, filename):
                break
    def debug(self, line, filename):
        for processor in self.debug_processors:
            if processor(line, filename):
                break

    def modems(self, line, filename):
        for processor in self.modem_processors:
            if processor(line, filename):
                break

    def sessions(self, line, filename):
        for processor in self.session_processors:
            if processor(line, filename):
                break

    def id(self, line, filename):
        for processor in self.id_processors:
            if processor(line, filename):
                break

    def memory(self, line, filename):
        for processor in self.memory_processors:
            if processor(line, filename):
                break

    def grading(self, line, filename):
        for processor in self.modem_grading_processors:
            if processor(line, filename):
                break

    def cpu(self, line, filename):
        for processor in self.cpu_processors:
            if processor(line, filename):
                break

    def modemevents(self, line, filename):
        for processor in self.modem_event_processors:
            if processor(line, filename):
                break

    def modemeventssorted(self, line, filename):
        for processor in self.modem_event_processors_sorted:
            if processor(line, filename):
                break

class ShellCommand(ShellOut):
    _command = ''

    def __init__(self, command):
        self._command = command

    def present(self):
        rv, is_present = self.ex("which {0!s}".format(self._command))
        return is_present

class Tar(ShellCommand):
    def __init__(self):
        super(Tar, self).__init__('tar')

    def expand(self, source_path, target_path):
        return self.ex("{0!s} xf {1!s} -C{2!s} 2>/dev/null".format(self._command, source_path, target_path))

class GZcat(ShellCommand):
    def __init__(self):
        super(GZcat, self).__init__('gzcat')

    def out(self, filename):
        # rvalue, worked = self.ex("{0!s} {1!s} 2>/dev/null".format(self._command,filename))
        rvalue, worked = self.ex("{0!s} -f {1!s} 2>/dev/null".format(self._command, filename))
        # if not worked:
           # raise SystemError("Error returned from gzcat: {0!s}".format(rvalue))

        return (rvalue, worked)

class Zcat(ShellCommand):
    def __init__(self):
        super(Zcat, self).__init__('zcat')

    def out(self, filename):
        #rvalue, worked = self.ex("{0!s} {1!s} 2>/dev/null".format(self._command,filename))
        rvalue, worked = self.ex("{0!s} -f {1!s} 2>/dev/null".format(self._command, filename))
        #if not worked:
            # raise SystemError("Error returned from zcat: {0!s}".format(rvalue))

        return (rvalue, worked)

class WorkDir(ShellOut):
    path = ''
    base = ''

    def __init__(self, base="~/.lula", name='unnamed'):
        if name is None or name == '':
            raise ValueError('the name in WorkDir was blank.')
        self.base = base
        self.path = os.path.join(os.path.expanduser(base), name)

    def exists(self):
        return os.path.exists(self.path)

    def create(self):
        self.ex("mkdir -p {0!s}".format(self.path))

    @classmethod
    def _abs_compare(cls, path1, path2):
        return os.path.samefile(os.path.abspath(os.path.expanduser(path1)), os.path.abspath(os.path.expanduser(path2)))

    def cleanup(self):
        if not self._abs_compare(self.base, self.path):
            if not self._abs_compare(self.path, '/'):
            # just a safety, never accidently try to delete the filesystem
                if len(os.path.relpath(self.path, self.base)) > 0:
                    shutil.rmtree(self.path, True)

class TargetFile(ShellOut):
    path = ''

    def __init__(self, path):
        self.path = path

    def exists(self):
        return os.path.exists(self.path)

    def basename(self):
        return os.path.basename(self.path)

class LogPackage(ShellOut):
    def __init__(self,
                 path,
                 timezone='US/Eastern',
                 daterange=DateRange(),
                 parse_type='known'):
        self.target_file = None
        self._work_dir = None
        self._daterange = None
        self.lp = None
        self.parse_type = parse_type

        self._daterange = daterange
        self.target_file = TargetFile(path)
        if not self.target_file.exists():
            print("quitting because that file doesn't exist")
            exit(2)
        self._prepare_temp_dir()
        self._untar_file()
        self.lp = LineProcessors()
        self.flp = FfmpegLineProcessors()
        self.lp.timezone = timezone
        self.flp.timezone = timezone
        self.lp.daterange = self._daterange
        self.lp.parse_type = parse_type
        self.flp.parse_type = parse_type

    def _prepare_temp_dir(self):
        self._work_dir = WorkDir(name=self.target_file.basename())
        self._work_dir.create()
        if not self._work_dir.exists():
            print("failed to make the temporary work dir, so quitting")
            exit(2)

    def _untar_file(self):
        tar = Tar()
        if not tar.present():
            print("Couldn't find the needed tar command.")
            exit(3)
        rv, worked = tar.expand(self.target_file.path, self._work_dir.path)
        if not worked:
            print("The untar failed with: {0!s}".format(rv))
            # Note purposefully leaving off an exit here as sometimes tar just returns 1 do to dmesg duplication

    def _find_compressed_logs(self):
        if self.parse_type == "ffmpeg" or self.parse_type == "ffmpegv" or self.parse_type == "ffmpega":
            match_string = 'ffmpeg_streamId__cdn_0__outputIndex__0.txt.*'
        else:
            match_string = 'messages.log.*'
        # all_files = glob.glob(os.path.join(self._work_dir.path,'messages.log.*.gz'))
        all_files = glob.glob(os.path.join(self._work_dir.path, match_string))
        # all_files.sort(cmp=lambda x, y: cmp(int(os.path.basename(x).split('.')[2]), int(os.path.basename(y).split('.')[2])), reverse=True)
        all_files.sort(key=functools.cmp_to_key(lambda x, y: cmp(int(os.path.basename(x).split('.')[2]), int(os.path.basename(y).split('.')[2]))), reverse=True)

        #Testing the sort
        # for file in all_files:
        #     print(file)
        # exit(3)

        return all_files

    def _find_all_logs(self):
        if self.parse_type == "ffmpeg" or self.parse_type == "ffmpegv" or self.parse_type == "ffmpega":
            match_string = 'ffmpeg_streamId__cdn_0__outputIndex__0.txt'
        else:
            match_string = 'messages.log'
        compressed_logs = self._find_compressed_logs()
        possible_current_log = os.path.join(self._work_dir.path, match_string)
        if os.path.exists(possible_current_log):
            compressed_logs.append(possible_current_log)

        #test the sort
        # for file in compressed_logs:
        #     print(file)
        # exit(3)

        return compressed_logs

    def _read_all_lines(self, process=None):
        gzcat = GZcat()
        zcat = Zcat()
        cat = gzcat

        if not gzcat.present():
            cat = zcat
            if not zcat.present():
                raise SystemError("Couldn't find the needed gzcat or zcat command.")
        # for filename in self._find_compressed_logs():
        for filename in self._find_all_logs():
            output, worked = cat.out(filename)
            if worked:
                for line in output.splitlines():
                    if process is None:
                        print(line)
                    else:
                        process(line, filename)
            else:
                print("Failed to read file: {0!s}".format(filename))

    def _return_semantic_only(self):
        #Print some header stuff in specific modes
        if self.lp.parse_type == 'md-bw':
            self.lp.print_csv_md_header()
        if self.lp.parse_type == 'md-db-bw':
            self.lp.print_csv_md_db_header()
        if self.lp.parse_type == 'bw':
            self.lp.print_csv_header()

        #All the real work takes place here
        if self.parse_type == "ffmpeg" or self.parse_type == "ffmpegv" or self.parse_type == "ffmpega":
            self._read_all_lines(process=self.flp.process)
        else:
            self._read_all_lines(process=self.lp.process)

        #Print some footer stuff in specifc modes
        if self.lp.parse_type == 'md':
            print("Parsed all modem lines, results:")
            ModemSummary.instance().output()
        elif self.lp.parse_type == 'sessions':
            SessionTracker.instance().close()
            SessionTracker.instance().outputAll()
        elif self.lp.parse_type == 'modemeventssorted':
            ConnectivitySummary.instance().outputReport()

parser = argparse.ArgumentParser(description='Process LiveU logs from 4.0 or later devices.')

parser.add_argument('file', nargs='?', help='The tar.bz2 tarball you want to parse.', default=None)
parser.add_argument('-t ', '--timezone', default=None, help="The timezone to convert timestamps to, possible options include 'US/Eastern', 'US/Central', 'US/Pacific', 'UTC', default is 'US/Eastern'")
parser.add_argument('-b ', '--begin', default=None, help='Optional start date and time, only show log messages of this time or newer. Use a format like 2015-02-27 21:10:12+00:00.  If you omit the TZ, the system TZ will be used.')
parser.add_argument('-e ', '--end', default=None, help='Optional end date and time, only show log messages of this time or older. Use a format like 2015-02-27 21:10:12+00:00.  If you omit the TZ, the system TZ will be used.')
parser.add_argument('-p ', '--parse', default='known', help='Which method of parsing to use, options are:' + CBLUE + ' known ' + CEND + '(looks for a small set of known errors and events, this is the default),' + CBLUE + ' error ' + CEND + '(return any line where the stirng ERROR appears),' + CBLUE + ' all ' + CEND + '(return all lines),' + CBLUE + ' bw ' + CEND + '(return a csv format of the stream bandwidth),' + CBLUE + ' md-bw ' + CEND + '(return a csv format of the modems bandwidth),' + CBLUE + ' md-db-bw ' + CEND + '(return a csv format of the data bridge modems bandwidth),' + CBLUE + ' v ' + CEND + '(verbose: include errors that are a bit more common),' + CBLUE + ' md ' + CEND + '(modem statistics), sessions (session summary),' + CBLUE + ' id ' + CEND + '(boss id of the device which is streaming to server and boss id of the server instance on which unit is streaming),' + CBLUE + ' memory ' + CEND + '(memory usage),' + CBLUE + ' grading ' + CEND + '(modem grading when modem goes to Limited service and back to Full service),' + CBLUE + ' cpu ' + CEND + '(cpu idle unit side or cpu usage server side), ' + CBLUE + 'modemevents' + CEND + ' (All events related to modem connectivity)' + CBLUE + 'modemeventssorted' + CEND + '(All events related to modem connectivity, sorted by modem)', choices=['known', 'error', 'all', 'bw', 'md-bw', 'md-db-bw', 'v', 'md', 'sessions', 'id', 'memory', 'grading', 'cpu', 'debug', 'ffmpeg', 'ffmpegv', 'ffmpega', 'modemevents', 'modemeventssorted'])
parser.add_argument('-v', '--version', default=False, help='Display the version then quit.', action='store_true')

class TimezoneFinder(object):
    def __init__(self, tz_from_cli):
        self.tz_from_cli = tz_from_cli
        self.settings_path = os.path.expanduser('~/.lula_tz')
        self._default = 'US/Eastern'
        self.best_setting = self._default

        self._find_best_setting()

    def _settings_file_exists(self):
        return os.path.exists(self.settings_path)

    def _settings_file(self):
        if self._settings_file_exists():
            fo = open(self.settings_path, 'r')
            temp_v = fo.read()
            fo.close
            temp_v = temp_v.strip()
            if temp_v is not None and temp_v != '':
                return temp_v
            else:
                return ''
        else:
            return ''

    def _find_best_setting(self):
        if self.tz_from_cli is not None:
            self.best_setting = self.tz_from_cli
        elif self._settings_file() != '':
            self.best_setting = self._settings_file()

ops = parser.parse_args()
tzf = TimezoneFinder(ops.timezone)
# print(tzf.best_setting)
# exit(100)

if ops.version:
    print("lula2 version {0!s}".format(VERSION))
    exit(0)
elif ops.file is None:
    parser.print_help()
    exit(1)
# elif ops.parse == "ffmpeg":
#     print("new ffmpeg mode")
#     exit(2)

dr = DateRange(start=ops.begin, end=ops.end)

# log_package = LogPackage(sys.argv[1])
# log_package = LogPackage(ops.file,timezone=ops.timezone, daterange=dr, parse_type=ops.parse)
log_package = LogPackage(ops.file, timezone=tzf.best_setting, daterange=dr, parse_type=ops.parse)
try:
    log_package._return_semantic_only()
except SystemError as e:
    if len(str(e)) <= 100:
        print("Error: {0!s}".format(e))
    else:
        print("Caught a SystemError but error output was too long to print.")
except KeyboardInterrupt as e:
    print("Interupt")
finally:
    log_package._work_dir.cleanup()