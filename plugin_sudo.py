#!/usr/bin/python
import dmenu_extended

if __name__ == "__main__":
    d = dmenu_extended.dmenu()
    d.load_preferences()
    # Find a way to hide the users password by setting the forground text colour
    # to match the background text colour (so it's not readable)
    if '-nb' in d.prefs['menu_arguments']:
        index_background = d.prefs['menu_arguments'].index('-nb') + 1
        if '-nf' in d.prefs['menu_arguments']:
            index_foreground = d.prefs['menu_arguments'].index('-nf') + 1
            d.prefs['menu_arguments'][index_foreground] = d.prefs['menu_arguments'][index_background]
        else:
            d.prefs['menu_arguments'] += ['-nf', d.prefs['menu_arguments'][index_background]]
    else:
        d.prefs['menu_arguments'] += ['-nf', '#000000']
        d.prefs['menu_arguments'] += ['-nb', '#000000']
    with open(dmenu_extended.path_plugins+'/plugin_sudo_couter.txt', 'r') as f:
        message = f.readline()
    pword = d.menu('', prompt=message)
    if pword == '':
        sys.exit()
    with open(dmenu_extended.path_plugins+'/plugin_sudo_couter.txt', 'w') as f:
        f.write('Password incorrect, try again:')
    print(pword+"\n")


class extension(dmenu_extended.dmenu):

    # Set the name to appear in the menu
    title = 'Sudo'

    # Determines whether to attach the submenu indicator
    is_submenu = True

    # Required function, runs when the user fires the menu item
    def run(self, inputText):
        self.execute("chmod +x " + dmenu_extended.path_plugins+'/plugin_sudo.py')
        cache = self.cache_open(dmenu_extended.file_cache).split('\n')
        item = self.menu(cache)
        with open(dmenu_extended.path_plugins+'/plugin_sudo_couter.txt', 'w') as f:
            f.write('Sudo password')
        self.execute('SUDO_ASKPASS="'+dmenu_extended.path_plugins+'/plugin_sudo.py" sudo -A ' + item)