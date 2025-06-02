import miramode
from miramode.const import OUTLET_STATE_STR, TIMER_STATE_STR


class Notifications(miramode.NotificationsBase):
    def __init__(self, event, is_pairing=False):
        self._event = event
        self._is_pairing = is_pairing

    def client_details(self, client_slot, client_name):
        print(f"{client_name}")
        self._event.set()

    def controls_operated(
            self, client_slot, change_made, timer_state, target_temperature,
            actual_temperature, outlet_state_1, outlet_state_2,
            remaining_seconds, succesful_update_command_counter):
        print(f"The command completed successfully")
        self._event.set()

    def device_state(
            self, client_slot, timer_state, target_temperature,
            actual_temperature, outlet_state_1, outlet_state_2,
            remaining_seconds, succesful_update_command_counter):
        print("Outlet 1: "
              f"{OUTLET_STATE_STR.get(outlet_state_1, outlet_state_1)}")
        print("Outlet 2: "
              f"{OUTLET_STATE_STR.get(outlet_state_2, outlet_state_2)}")
        print(f"Target temperature: {target_temperature:.1f}C")
        print(f"Actual temperature: {actual_temperature:.1f}C")
        print(f"Timer state: {TIMER_STATE_STR.get(timer_state, timer_state)}")
        print(f"Remaining seconds: {remaining_seconds}")
        self._event.set()

    def slots(self, client_slot, slots):
        self.slots = slots
        self._event.set()

    def success_or_failure(self, client_slot, status):
        if status == miramode.FAILURE:
            print(f"The command failed")
        elif self._is_pairing:
            print(f"Assigned client slot: {status}")
        elif status == miramode.SUCCESS:
            print(f"The command completed successfully")
        else:
            raise Exception(f"Unrecognized status: {status}")
        self._event.set()
