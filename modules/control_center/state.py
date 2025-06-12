# modules/control_center/state.py
from ignis.variable import Variable

# Zmienna przechowująca nazwę aktywnego widoku w Control Center
# Domyślnie ustawiamy na 'notifications'
active_view = Variable("notifications")