import sys
import re
import datetime
import logging

def setup_logging():
    logging.basicConfig(
        filename='app_debug.log', 
        level=logging.DEBUG, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

class StdErrRedirector:
    """Captures stderr (tqdm progress bars) to update the GUI."""
    def __init__(self, callback):
        self.callback = callback
        self.original_stderr = sys.stderr

    def write(self, buf):
        if self.original_stderr:
            self.original_stderr.write(buf)
        match = re.search(r'(\d+)%', buf)
        if match:
            try:
                self.callback(int(match.group(1)) / 100.0)
            except: pass

    def flush(self):
        if self.original_stderr:
            self.original_stderr.flush()

    def start(self):
        sys.stderr = self

    def stop(self):
        sys.stderr = self.original_stderr

def format_timestamp(seconds):
    """Converts seconds (float) to SRT timestamp format (HH:MM:SS,mmm)"""
    td = datetime.timedelta(seconds=seconds)
    # total_seconds = int(td.total_seconds())
    # hours = total_seconds // 3600
    # minutes = (total_seconds % 3600) // 60
    # secs = total_seconds % 60
    # millis = int(td.microseconds / 1000)
    # return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"
    
    # Cleaner approach using str(timedelta) but handling comma
    s = str(td)
    if '.' not in s: s += ".000"
    s = s.replace('.', ',')
    # Pad hours if needed (timedelta usually does H:MM:SS only if H>0)
    parts = s.split(':')
    if len(parts) == 2:
        s = "00:" + s
    return s[:12] # Trim microsecond precision to 3 digits

def create_srt_content(segments):
    """
    Generates SRT formatted string from segments list.
    Each segment: {'start': float, 'end': float, 'text': str}
    """
    srt_output = ""
    for i, seg in enumerate(segments):
        start = format_timestamp(seg.get('start', 0))
        end = format_timestamp(seg.get('end', 0))
        text = seg.get('text', '').strip()
        
        srt_output += f"{i+1}\n{start} --> {end}\n{text}\n\n"
    return srt_output
