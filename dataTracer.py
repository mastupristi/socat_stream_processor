#  Copyright 2024 Massimiliano Cialdi
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

def dataTracer(data, verbose=False, hexadecimal=False):
    if not verbose and not hexadecimal:
        return  # Do not print anything if no option is active

    # Determines whether 'date' is a string or byte
    if isinstance(data, str):
        data = data.encode('utf-8')  # Convert string to bytes
    # Create a hexadecimal representation of the text
    if hexadecimal:
        hex_lines = []
        # Split data into blocks of 16 characters
        for i in range(0, len(data), 16):
            # Extracting a bytes block
            chunk = data[i:i+16]
            # Convert each byte to hexadecimal
            hex_string = ' '.join(f"{byte:02x}" for byte in chunk)
            # Add the formatted line to the result
            if verbose:
                # If verbose is also active, include the text next to the hexadecimal
                printable_line = ''.join(chr(byte) if 32 <= byte < 127 else '.' for byte in chunk)
                hex_lines.append(f"{hex_string.ljust(47)}  {printable_line}")
            else:
                hex_lines.append(hex_string)

        # Printing of hexadecimal lines
        print("\n".join(hex_lines))
    elif verbose:
        # If only verbose is active, try decoding and print plain text
        try:
            text = data.decode('utf-8')
            print(text)
        except UnicodeDecodeError:
            print("Data contains bytes that cannot be decoded in UTF-8")
