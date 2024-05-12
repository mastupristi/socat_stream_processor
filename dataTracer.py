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
