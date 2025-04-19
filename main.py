# MADE BY THETNTTEAM
# https://github.com/Thetntteam/streamdeck-desktop-streamer/

import os
import time
from PIL import Image, ImageOps
from mss import mss
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper
from StreamDeck.Transport.Transport import TransportError

import ctypes

# Load hidapi.dll manually if needed (adjust path if required)
ctypes.CDLL(os.path.abspath("hidapi.dll"))

# Capture screen function
def capture_screen():
    with mss() as sct:
        screen = sct.grab(sct.monitors[1])  # Use the primary monitor (monitors[1] is typically the main display)
    return screen

# Generate the full deck-sized image
def create_full_deck_sized_image(deck, key_spacing, screen_image):
    key_rows, key_cols = deck.key_layout()
    key_width, key_height = deck.key_image_format()['size']
    spacing_x, spacing_y = key_spacing

    # Compute the total size of the full StreamDeck image
    key_width *= key_cols
    key_height *= key_rows
    spacing_x *= key_cols - 1
    spacing_y *= key_rows - 1

    full_deck_image_size = (key_width + spacing_x, key_height + spacing_y)

    # Resize the screen capture to fit the StreamDeck layout
    screen_image_resized = screen_image.resize(full_deck_image_size, Image.LANCZOS)
    return screen_image_resized

# Crop the key image from the full deck-sized image
def crop_key_image_from_deck_sized_image(deck, image, key_spacing, key):
    key_rows, key_cols = deck.key_layout()
    key_width, key_height = deck.key_image_format()['size']
    spacing_x, spacing_y = key_spacing

    # Determine which row and column the requested key is located on
    row = key // key_cols
    col = key % key_cols

    # Compute the starting X and Y offsets into the full-size image
    start_x = col * (key_width + spacing_x)
    start_y = row * (key_height + spacing_y)

    # Compute the region of the larger deck image that is occupied by the given key
    region = (start_x, start_y, start_x + key_width, start_y + key_height)
    segment = image.crop(region)

    # Create a new key-sized image and paste in the cropped section of the full image
    key_image = PILHelper.create_key_image(deck)
    key_image.paste(segment)

    return PILHelper.to_native_key_format(deck, key_image)

# Handle key state changes
def key_change_callback(deck, key, state):
    if state:
        # Reset deck and stop the stream if any key is pressed
        with deck:
            deck.reset()
            deck.close()

# Main execution function
def stream_to_deck(deck):
    key_spacing = (36, 36)  # Approximate spacing between keys, adjust if needed

    # Capture the screen and resize it
    screenshot = capture_screen()
    screen_image = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)

    # Resize screen image to match the full StreamDeck layout
    full_deck_image = create_full_deck_sized_image(deck, key_spacing, screen_image)

    # Crop and set images for each key
    key_images = {}
    for k in range(deck.key_count()):
        key_images[k] = crop_key_image_from_deck_sized_image(deck, full_deck_image, key_spacing, k)

    with deck:
        # Apply the key images to the Stream Deck buttons
        for k in range(deck.key_count()):
            deck.set_key_image(k, key_images[k])

        # Set the callback to stop streaming on key press
        deck.set_key_callback(key_change_callback)

        # Keep updating the Stream Deck with new images from the screen
        while True:
            screenshot = capture_screen()
            screen_image = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)
            full_deck_image = create_full_deck_sized_image(deck, key_spacing, screen_image)

            key_images = {}
            for k in range(deck.key_count()):
                key_images[k] = crop_key_image_from_deck_sized_image(deck, full_deck_image, key_spacing, k)

            # Update key images
            for k in range(deck.key_count()):
                deck.set_key_image(k, key_images[k])

            time.sleep(0.1)

# Main execution
if __name__ == "__main__":
    streamdecks = DeviceManager().enumerate()

    if len(streamdecks) == 0:
        print("No Stream Decks found.")
        exit()

    deck = streamdecks[0]
    deck.open()
    deck.reset()

    print("Opened '{}' device (serial number: '{}')".format(deck.deck_type(), deck.get_serial_number()))

    # Set initial brightness to 30%
    deck.set_brightness(100)

    # Start the screen streaming
    stream_to_deck(deck)
