import param
import panel as pn

"""
This module is a storehouse of utility codes that are only used at the highest
level of the interface. These are convenience functions for rapid prototyping
of UIs. 
"""


class StatusBar(param.Parameterized):
    """ Status bar as a simple textbox and associated convenience functions """
    status = param.String(default='', label='', precedence=1)

    def set_msg(self, message):
        self.status = message

    def busy(self):
        self.status = 'Busy ... '

    def clear(self):
        self.status = ''

    @param.depends('status', watch=True)
    def panel(self):
        return pn.panel(
            self.param, parameters=['status'], widgets={'status': pn.widgets.TextInput(sizing_mode='stretch_width')},
            show_name=False)
