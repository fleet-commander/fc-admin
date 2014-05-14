import subprocess
import os
import time
import signal

class SpiceSessionManager:
  XSPICE = 'Xspice :10 --disable-ticketing --port 8182'
  GNOME_SESSION = 'DISPLAY=:10 gnome-session'
  #GNOME_SHELL = 'gnome-shell'
  GSETTINGS_LOGGER = 'fc-gsettings-logger'

  def __init__(self):
    self.env = os.environ.copy()
    self.env['DISPLAY'] = ':10'
    self.xspice = None
    self.gnome_session = None
    self.gnome_shell = None
    self.gsettings_logger = None

  def start(self):
    DNULL = open('/dev/null', 'w')
    template = "su -c \"%s\" - fc-user"
    self.xspice = subprocess.Popen(template % self.XSPICE, shell=True, stdout=DNULL, stderr=DNULL, stdin=DNULL)
    time.sleep(1)
    self.gnome_session = subprocess.Popen(template % self.GNOME_SESSION, shell=True, stdout=DNULL, stderr=DNULL, stdin=DNULL)
    #self.gnome_shell = subprocess.Popen(template % self.GNOME_SHELL, shell=True)
    self.gsettings_logger = subprocess.Popen(template % self.GSETTINGS_LOGGER, shell=True, stdin=DNULL, stdout=DNULL, stderr=DNULL)

  def stop(self):
    if not self.gsettings_logger and not self.gnome_session and not self.xspice:
      return

    if self.gsettings_logger:
      self.gsettings_logger.terminate()
    if self.gnome_session:
      self.gnome_session.terminate()
    if self.xspice:
      self.xspice.terminate()
    
    if self.gsettings_logger and self.gsettings_logger.poll() == None:
      self.gsettings_logger.kill()
    if self.gnome_session and self.gnome_session.poll() == None:
      self.gnome_session.kill()
    if self.xspice and self.xspice.poll() == None:
      self.xspice.kill()

if __name__ == '__main__':
  session = SpiceSessionManager()
  session.start()

  def sigint_handler(sig, frm):
    session.stop()

  signal.signal(signal.SIGINT, sigint_handler)

  signal.pause()

