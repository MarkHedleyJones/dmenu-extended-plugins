import dmenu_extended
import sys

class extension(dmenu_extended.dmenu):

    # Set the name to appear in the menu
    title = 'Example extension'

    # Determines whether to attach the submenu indicator
    is_submenu = True


    # Required function, runs when the user fires the menu item
    def run(self, inputText):

        if inputText != '':
            self.menu('Extra information was passed')
        else:
            self.menu('You have just fired the example plugin')