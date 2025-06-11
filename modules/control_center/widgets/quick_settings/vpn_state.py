# modules/control_center/widgets/quick_settings/vpn_state.py
from ignis.variable import Variable

# Globalna, współdzielona zmienna przechowująca stan połączenia PracaVPN
praca_vpn_is_active = Variable(False)