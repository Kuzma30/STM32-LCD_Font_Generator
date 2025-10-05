from PIL import Image, ImageFont, ImageDraw
import argparse
import math
import regex as re
import time
import textwrap

# Greyscale threshold from 0 - 255
THRESHOLD = 128
# Font Character Set
CHAR_SET = '!"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмнопрстуфхцчшщъыьэюя'

def get_charset_perceived():
    # https://stackoverflow.com/questions/6805311/playing-around-with-devanagari-characters
    return re.findall(r'\X', CHAR_SET)

def get_max_width(font):
    widths = []
    for ch in get_charset_perceived():
        bbox = font.getbbox(ch)
        w, h = bbox[2], bbox[3]
        widths.append(w)
    return max(widths)

def bin_to_c_binary_array(bin_text, bytes_per_line, lsb_padding=0, msb_padding=0):
    # Create comment with preview of line
    comment = bin_text.replace('0', ' ').replace('1', '#')

    # Pad the top or bottom remaining bits with 0's
    bin_text = ("0" * msb_padding) + bin_text + ("0" * lsb_padding)
    # Ensure the length matches the number of bytes
    assert len(bin_text) == (bytes_per_line * 8)

    # Split into individual bits
    bit_list = list(bin_text)
    # Join bits with commas
    array = ', '.join(bit_list)

    return f'{array},\n'#, ;|{comment}|\n'

def generate_font_data(font, x_size, y_size):
    data = ''

    # Find bytes per line needed to fit the font width
    bytes_per_line = math.ceil(x_size / 8)
    empty_bit_padding = (bytes_per_line * 8 - x_size)

    for i, ch in enumerate(get_charset_perceived()):
        # The starting array index of the current char
        array_offset = i * (bytes_per_line * 8 * y_size)

        # Calculate size and margins for centered text
        text_bbox = font.getbbox(ch)
        w, h = text_bbox[2], text_bbox[3]
        x_margin = (x_size - w) // 2
        y_margin = (y_size - h) // 2
        margin = (x_margin, y_margin)
        im_size = (x_size, y_size)

        # Create image and write the char
        im = Image.new("RGB", im_size)
        drawer = ImageDraw.Draw(im)
        drawer.text(margin, ch, font=font)
        del drawer

        # For each row, convert to binary representation
        for y in range(y_size):
            # Get list of row pixels
            x_coordinates = range(x_size)
            pixels = map(lambda x: im.getpixel((x, y))[0], x_coordinates)
            # Convert to binary text
            bin_text = map(lambda val: '1' if val > THRESHOLD else '0', pixels)
            bin_text = ''.join(bin_text)
            # Convert to C-style binary array of individual bits
            data += bin_to_c_binary_array(bin_text, bytes_per_line,
                                         lsb_padding=empty_bit_padding)
    return data

def output_files(font, font_width, font_height, font_data, font_name):
    generated_time = time.strftime("%Y-%m-%d %H:%M:%S")

    # Create filename, remove invalid chars
    filename = f'Font{font_name}{font_height}'
    filename = ''.join(c if c.isalnum() else '' for c in filename)

    # C file template with binary radix
    output = f"""
memory_initialization_radix = 2;
memory_initialization_vector =
{font_data}
"""
    # Output font C header file
    with open(f'{filename}.coe', 'w') as f:
        f.write(output)

    # Output preview of font
    preview_bbox = font.getbbox(CHAR_SET)
    size = (preview_bbox[2], preview_bbox[3])
    im = Image.new("RGB", size)
    drawer = ImageDraw.Draw(im)
    drawer.text((0, 0), CHAR_SET, font=font)
    im.save(f'{filename}.png')

if __name__ == '__main__':
    # Command-line arguments
    parser = argparse.ArgumentParser(
        description='Generate text font for STM32xx-EVAL\'s LCD driver')

    parser.add_argument('-f', '--font',
                        type=str,
                        help='Font type [filename]',
                        required=True)
    parser.add_argument('-s', '--size',
                        type=int,
                        help='Font size in pixels [int]',
                        default=16,
                        required=False)
    parser.add_argument('-n', '--name',
                        type=str,
                        help='Custom font name [str]',
                        required=False)
    parser.add_argument('-c', '--charset',
                        type=str,
                        help='Custom charset from file [filename]',
                        required=False)
    args = parser.parse_args()

    if args.charset:
        with open(args.charset) as f:
            CHAR_SET = f.read().splitlines()[0]

    # Create font type
    font_type = args.font
    font_height = args.size

    myfont = ImageFont.truetype(font_type, size=font_height)
    font_width = get_max_width(myfont)

    if args.name:
        font_name = args.name
    else:
        font_name = myfont.font.family

    # Generate the C file data
    font_data = generate_font_data(myfont, font_width, font_height)
    
    # Output everything
    output_files(font=myfont,
                 font_width=font_width,
                 font_height=font_height,
                 font_data=font_data,
                 font_name=font_name)