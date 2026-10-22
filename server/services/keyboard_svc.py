from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
import time

keyboard = KeyboardController()
mouse = MouseController()

# Map string names to pynput Key objects
KEY_MAP = {
    "ctrl": Key.ctrl,
    "shift": Key.shift,
    "alt": Key.alt,
    "f13": Key.f13,
    "f14": Key.f14,
    "f15": Key.f15,
    "c": "c",
    "v": "v",
    "x": "x",
    "z": "z",
    "y": "y",
    "a": "a",
    # media keys
    "media_play_pause": Key.media_play_pause,
    "media_next": Key.media_next,
    "media_previous": Key.media_previous,
    "media_volume_up": Key.media_volume_up,
    "media_volume_down": Key.media_volume_down,
    "media_volume_mute": Key.media_volume_mute
}

def press_hotkey(keys_list: list[str]):
    """Presses a combination of keys together."""
    parsed_keys = [KEY_MAP.get(k.lower(), k.lower()) for k in keys_list]
    for k in parsed_keys: keyboard.press(k)
    for k in reversed(parsed_keys): keyboard.release(k)

def send_copy(): press_hotkey(["ctrl", "c"]); time.sleep(0.1)
def send_paste(): press_hotkey(["ctrl", "v"])
def send_cut(): press_hotkey(["ctrl", "x"]); time.sleep(0.1)
def send_undo(): press_hotkey(["ctrl", "z"])
def send_select_all(): press_hotkey(["ctrl", "a"])
    
def send_media(action: str):
    valid_actions = {"play_pause": "media_play_pause", "next": "media_next", "prev": "media_previous"}
    if action in valid_actions: press_hotkey([valid_actions[action]])

def type_text(text: str):
    keyboard.type(text)

def move_mouse(dx: int, dy: int):
    mouse.move(dx, dy)

def click_mouse(btn: str, double: bool = False):
    b = Button.right if btn == "right" else Button.middle if btn == "middle" else Button.left
    mouse.click(b, 2 if double else 1)

def scroll_mouse(dy: int):
    mouse.scroll(0, dy)
