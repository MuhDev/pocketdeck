import pyperclip

def read_clipboard() -> str:
    try:
        return pyperclip.paste()
    except Exception as e:
        print(f"Error reading clipboard: {e}")
        return ""

def write_clipboard(text: str):
    try:
        pyperclip.copy(text)
    except Exception as e:
        print(f"Error writing to clipboard: {e}")
