import dmenu_extended
import sys
import datetime
import os
import subprocess
import json
import pexpect
import keyring

path_config  = dmenu_extended.path_prefs + '/jrnl.txt'

class extension(dmenu_extended.dmenu):

  # Set the name to appear in the menu
  title = 'Jrnl'

  # Determines whether to attach the submenu indicator
  is_submenu = True
  config = None
  current_journal = None
  jrnl_installed = False
  jrnl_configured = False
  passwords = {}
  bodies_current_journal_flag = False

  def __init__(self):
    self.startup_checks()

  def startup_checks(self):
    for path in self.system_path():
      if not os.path.exists(path):
          continue
      if 'jrnl' in os.listdir(path):
        self.jrnl_installed = True
        break

    if os.path.isfile(os.path.expanduser('~') + '/.jrnl_config'):
      self.jrnl_configured = True
    else:
      self.jrnl_configured = False

    self.config = {}

    if self.jrnl_configured:
      self.config = self.load_json(os.path.expanduser('~') + '/.jrnl_config')
    # Override any jrnl config settings with local settings
    config = self.load_config()
    self.current_journal = "default"
    for pref in config:
      self.config[pref] = config[pref]

  def update_config(self):
    tmp = self.load_json(os.path.expanduser('~') + '/.jrnl_config')
    for item in tmp:
      self.config[item] = tmp[item]

  def load_config(self):
    defaults = {
      "default_settings": {
        "gui_editor": False,
        "indicator_has_body": '*',
        "indicator_no_body": '-',
        "display_entry_titles_only": True,
        "keep_open_after_edit": False
      },
      "user_settings": {
      }
    }
    if os.path.isfile(path_config):
      tmp = self.load_json(path_config)

      # check for new options (upade as necessary)
      match = True
      if 'default_settings' not in tmp:
        match = False
        tmp['default_settings'] = {}
      if 'user_settings' not in tmp:
        match = False
        tmp['user_settings'] = {}

      for key in defaults['default_settings']:
        if key not in tmp['default_settings'] or tmp['default_settings'][key] != defaults['default_settings'][key]:
          match = False

      if match == False:
        for key in defaults['default_settings']:
          tmp['default_settings'][key] = defaults['default_settings'][key]
        self.save_json(path_config, tmp)

      for key in tmp['user_settings']:
        defaults['default_settings'][key] = tmp['user_settings'][key]
      return defaults['default_settings']
    else:
      self.save_json(path_config, defaults)
      return defaults['default_settings']


  def get_journal_password(self, journal=None):
    print("get journal password")
    if journal is None:
      journal = self.current_journal

    if journal in self.passwords:
      return self.passwords[journal]
    else:
      pword = self.get_password(helper_text=journal)
      self.passwords[journal] = pword
      return pword

  def setup_jrnl(self):
    command = "jrnl"
    path = self.menu("~/journal.txt", prompt="Path to your journal file:")
    encrypt = self.menu("No\nYes", prompt="Encrypt your journal?:")
    if encrypt == "Yes":
      pword = self.get_password(helper_text="encryption password")
      store_in_keychain = self.menu("No\nYes", prompt="Store password in system keychain?:\n")
    proc = pexpect.spawn(command)
    proc.expect(["Path to your journal file.*"])
    proc.sendline(path)
    proc.expect(["Enter password for journal.*"])
    if encrypt == "Yes":
      proc.sendline(pword)
      proc.expect(["Do you want to store the password in your keychain?.*"])
      if store_in_keychain.lower()[0] == 'y':
        proc.sendline('Y')
      else:
        proc.sendline('n')
    else:
      proc.sendline("")
    proc.expect([".*Compose Entry.*"])
    proc.close()
    self.startup_checks()


  def run_journal_command(self, command, journal=None, output=True, timeout=1):
    print("run journal command")
    if journal is None:
      journal = self.current_journal

    jrnl_json = None
    if self.journal_is_encrypted():

      try:
        command = " ".join(command)
        proc = pexpect.spawn(command, timeout=timeout)
        if self.journal_password_managed(journal=journal) == False:
          proc.expect(["Password: "])
          # if "password" in self.config["journals"][journal]:
          #   pword = self.config["journals"][journal]["password"]
          # else:
          #   pword = self.menu(" ", prompt="Password ("+self.current_journal+"): ")
          # pword = self.get_journal_password(journal)
          # proc.sendline(pword)
          proc.sendline(self.get_journal_password(journal))
        if output:
          print("Expecting output")
          jrnl_json = proc.read()
        proc.expect(pexpect.EOF)
        proc.close()
        # if self.journal_password_managed(journal) == False:
        #   self.config["journals"][journal]["password"] = pword
      except pexpect.exceptions.TIMEOUT:
        print("except")
        if output:
          out = self.menu("Incorrect password", prompt="")
          sys.exit()

    else:
      jrnl_json = subprocess.check_output(command)

    if output and jrnl_json is None:
      out = self.menu("There was an error dealing with the journal", prompt="Warning: ")
    return jrnl_json


  def get_journal(self, journal=None):
    print("get journal")
    if journal is None:
      journal is self.current_journal
    command = ["jrnl"]
    if journal is not None and journal in self.config["journals"]:
        command.append(journal)
    command = command + ["--export", "json"]
    jrnl_json = self.run_journal_command(command, journal)
    tmp = json.loads(jrnl_json)
    out = []
    for entry in tmp['entries']:

      if entry['body'] != '' and entry['body'] != '\n':
        self.bodies_current_journal_flag = True

      line = entry['date'] + ' '
      if entry['body'] != '\n' and entry['body'] != '':
        line += self.config["indicator_has_body"] + ' '
      else:
        line += self.config["indicator_no_body"] + ' '

      line += entry['title'].rstrip(' ')

      if self.config["display_entry_titles_only"] == False and entry['body'] != '\n':
        if line[-1:] != '.':
          line += '.'
        line.rstrip(' ')
        line += ' '
        line += entry['body']
      line = line.replace('\n', ' ')
      out.append(line)
    out.sort(reverse=True)
    return out

  def encrypt_journal(self, journal=None):
    print("encrypt journal")
    if journal is None:
      journal is self.current_journal

    pword = None

    command = ["jrnl", journal, "--encrypt"]
    print('step')
    print(" ".join(command))
    proc = pexpect.spawn(" ".join(command), timeout=10)
    print('step')
    if self.journal_is_encrypted(journal=journal) and \
      self.journal_password_managed(journal=journal) == False:
      proc.expect(["Password: "])
      # if "password" in self.config["journals"][journal]:
      #   pword = self.config["journals"][journal]["password"]
      # else:
      #   pword = self.menu(" ", prompt="Password ("+self.current_journal+"): ")
      proc.sendline(self.get_journal_password(journal))
    proc.expect(["Enter new password: "])
    print('step')
    pword = self.get_password(helper_text="create new password")
    kchain = self.menu(["No", "Yes"], prompt="Add password to your keychain?")
    print('step')
    print(pword)
    print(kchain)
    proc.sendline(pword)
    print('step')
    proc.expect(["Do you want to store the password in your keychain.*"])
    print('step')
    if kchain == "Yes":
      proc.sendline("Y")
    else:
      proc.sendline("n")
      # keyring.delete_password("jrnl", journal)
    proc.expect(pexpect.EOF)
    proc.close()
    self.passwords[journal] = pword
    # self.config["journals"][journal]["password"] = pword
    # self.update_config()


  def decrypt_journal(self, journal=None):
    print("decrypt journal")
    if journal is None:
      journal is self.current_journal
    self.run_journal_command(["jrnl", journal, "--decrypt"], output=False, timeout=5)
    # self.update_config()

  def journal_is_encrypted(self, journal=None):
    print(self.config["journals"])
    print("journal encrypted?"),
    self.update_config()
    if journal is None:
      journal = self.current_journal

    if "encrypt" in self.config["journals"][self.current_journal] and \
      self.config["journals"][self.current_journal]["encrypt"] == True:
      if keyring.get_password("jrnl", journal) is not None:
        self.config["journals"][self.current_journal]["managed"] = True
      else:
        self.config["journals"][self.current_journal]["managed"] = False
      print("yes")
      return True
    else:
      print("no")
      return False

  def journal_password_managed(self, journal=None):
    print("journal managed?"),
    if journal is None:
        journal = self.current_journal

    if self.journal_is_encrypted(journal):
      if self.config["journals"][self.current_journal]["managed"]:
        print("yes")
        return True
      else:
        print("no")
        return False
    else:
      print("no")
      return False


  def settings(self):
    print("settings")
    options = [
      self.prefs['indicator_edit'] + " Edit jrnl preferences",
      self.prefs['indicator_edit'] + " Edit plugin preferences"
    ]
    if self.journal_is_encrypted():
      options.append(self.prefs['indicator_submenu'] + " Decrypt journal (remove password for '"+self.current_journal+"')")
      options.append(self.prefs['indicator_submenu'] + " Change password for '"+self.current_journal+"'")
    else:
      options.append(self.prefs['indicator_submenu'] + " Encrypt journal (add password to '"+self.current_journal+"')")
    options.append(self.prefs['indicator_submenu'] + " Return")
    out = self.select(options)
    if out == options[0]:
      self.open_file(os.path.expanduser('~') + '/.jrnl_config')
    elif out == options[1]:
      self.open_file(path_config)
    elif out == options[2]:
      if self.journal_is_encrypted():
        self.decrypt_journal(self.current_journal)
        self.main()
      else:
        self.encrypt_journal(self.current_journal)
        self.main()
    elif out == self.prefs['indicator_submenu'] + " Change password for '"+self.current_journal+"'":
      self.encrypt_journal(self.current_journal)



  def edit(self, entry, date):
    print("editing entry")
    date_str = date.strftime(self.config['timeformat'])
    if self.config["gui_editor"]:
      # Gui based
      command = ["jrnl", self.current_journal, "-from", date_str, "-to", date_str, "--edit"]
      # self.execute("jrnl -from {date} -to {date} --edit".format(date=date_str))
      self.run_journal_command(command, output=False, timeout=None)
      if self.config["keep_open_after_edit"]:
        return
    else:
      # Terminal based
      self.open_terminal("jrnl -from {date} -to {date} --edit".format(date=date_str))

  def iso_date_str(self, date_in):
    return date_in.strftime("%Y-%m-%d")

  def add_entry(self):
    print("adding entry")
    today = datetime.datetime.today()
    daydiff = datetime.timedelta(days=1)
    opts = [
      self.prefs['indicator_submenu'] + " " + self.iso_date_str(today) + " - Today (" + today.strftime("%A") + ")",
      self.prefs['indicator_submenu'] + " " + self.iso_date_str(today) + " - Yesterday (" + (today - daydiff).strftime("%A") + ")",
    ]

    for i in range(2,256):
      out = [self.prefs['indicator_submenu']]
      # tmp = datetime.timedelta(days=i)
      dtmp = today - i * daydiff
      out.append(self.iso_date_str(dtmp))
      out.append("-")

      if i < 7:
        out.append(dtmp.strftime("%A"))
      elif i <= 13:
        out.append("Last")
        out.append(dtmp.strftime("%A"))
      elif i <= 22:
        out.append(dtmp.strftime("%A"))
        out.append("before last")
      else:
        out.append(dtmp.strftime("%A %d %B"))

      opts.append(" ".join(out))

    date = self.select(opts, prompt="Entry date: ")[len(self.prefs['indicator_submenu']) + 1:len(self.prefs['indicator_submenu']) + 11]
    content = self.menu(" ", prompt=date + ": ")
    command = ["jrnl", self.current_journal, date + ":", content]
    self.run_journal_command(command, self.current_journal)
    # subprocess.call(["jrnl", date + ":", content])

  def view_short_entries(self, state):
    self.config["display_entry_titles_only"] = state

  def switch_journal(self, journal_name):
    print("Switching to journal: " + journal_name)
    self.current_journal = journal_name

  def main(self):

    if self.jrnl_configured == False:
      print("jrnl not configured")
      self.setup_jrnl()
    else:
      print("jrnl configured")

    while True:
      print("main")
      # Prompt the user to install jrnl if not already installed
      if self.jrnl_installed == False:
        options = [
          "Could not find jrnl - do you have it installed?"
        ]
        options.append(self.prefs["indicator_submenu"] + " Visit jrnl website")
        out = self.select(options, prompt="Error!")
        if out == options[1]:
          self.open_url("http://jrnl.sh")
        sys.exit()

      options = [
        self.prefs['indicator_submenu'] + " New entry",
      ]

      journal_data = self.get_journal(self.current_journal)

      if len(journal_data) > 0 and self.bodies_current_journal_flag == True:
        if self.config["display_entry_titles_only"] == True:
          options.append(self.prefs['indicator_submenu'] + " Show full entries")
        else:
          options.append(self.prefs['indicator_submenu'] + " Show only titles")

      journal_switch_prefix = self.prefs['indicator_submenu'] + " Switch to '"

      for journal_name in [a for a in self.config["journals"] if a != self.current_journal]:
        options.append(journal_switch_prefix + journal_name + '\'')

      options = options + [self.prefs['indicator_submenu'] + " Settings"]
      options = options + journal_data
      out = self.select(options)

      if out == options[0]:
        self.add_entry()
      elif out == self.prefs['indicator_submenu'] + " Settings":
        self.settings()
        sys.exit()
      elif out == self.prefs['indicator_submenu'] + " Show full entries" or \
           out == self.prefs['indicator_submenu'] + " Show only titles":
        if self.config["display_entry_titles_only"]:
          self.view_short_entries(False)
        else:
          self.view_short_entries(True)
      elif out[:len(journal_switch_prefix)] == journal_switch_prefix:
        print("Switching journals")
        self.switch_journal(out[len(journal_switch_prefix):-1])
      else:
        entry_date = None
        try:
          date_length = len(datetime.datetime.today().strftime(self.config['timeformat']))
          entry_date = datetime.datetime.strptime(out[:date_length], self.config['timeformat'])
        except:
          pass
        if entry_date is not None:
          self.edit(out, entry_date)

  def run(self, input_text):
    self.main()
