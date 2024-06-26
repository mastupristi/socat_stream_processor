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

import socket
import argparse
import threading
import random
import signal
import sys
import textwrap
from tracer import create_tracer
from dataTracer import dataTracer



# Gestione del segnale di interruzione (Ctrl+C)
def signal_handler(stop_event, tracer):
    tracer.info("Signal received, stopping threads...")
    stop_event.set()

def disturb(data, error_rate, deletion_chance, rng):
    result = bytearray()
    for byte in data:
        if rng.random() < error_rate:
            if rng.random() < deletion_chance:
                continue
            byte ^= 1 << rng.randint(0, 7)
        result.append(byte)
    return bytes(result)

def dataDump(data, verbose, hexadecimal, dirChar, length, startingchar):
    if verbose or hexadecimal:
        import datetime
        current_time = datetime.datetime.now()
        print(f"{dirChar} {current_time.strftime('%Y-%m-%d %H:%M:%S.%f')} length={length} from={startingchar} to={startingchar+length-1}")
        dataTracer(data, verbose, hexadecimal)
        print("--")


def handle_connection(src_socket, dst_socket, seed, error_rate, deletion_chance, verbose, hexadecimal, dirChar, stop_event, tracer):
    outgoingByte = 0
    tracer.info("thread started")
    tracer.debug("Random numnber generator seeded with %d" %seed)
    rng = random.Random(seed)
    src_socket.settimeout(0.25)  # Set timeout to 250ms for the source socket
    try:
        while not stop_event.is_set():
            try:
                data = src_socket.recv(1024)
                if not data:
                    break
                disturbed_data = disturb(data, error_rate, deletion_chance, rng)
                dataDump(disturbed_data, verbose, hexadecimal, dirChar, len(disturbed_data), outgoingByte)
                outgoingByte += len(disturbed_data)
                dst_socket.sendall(disturbed_data)
            except socket.timeout:
                continue  # Continue the loop if timeout occurs, check the stop event
    except Exception as e:
        tracer.error(f"Error in thread {e}")
    finally:
        tracer.warning("thread end")
    stop_event.set()


def main(args):

    tracer = create_tracer(__name__, args.debug)
    tracer.info("Starting")
    # Prepare connections
    socket_A = socket.create_connection((*args.host_a,))
    socket_B = socket.create_connection((*args.host_b,))

    tracer.info("Socket created A %d and B %d" % (socket_A.fileno(), socket_B.fileno()))

    # Event to signal threads to stop
    stop_event = threading.Event()
    signal.signal(signal.SIGINT, lambda s, f: signal_handler(stop_event, tracer))

    # Create and start threads
    thread_AB = threading.Thread(target=handle_connection, args=(socket_A, socket_B, args.seed_AB, args.error_rate, args.deletion_chance, args.v, args.x, '>', stop_event, tracer), name="A->B")
    thread_BA = threading.Thread(target=handle_connection, args=(socket_B, socket_A, args.seed_BA, args.error_rate, args.deletion_chance, args.v, args.x, '<', stop_event, tracer), name="B->A")

    thread_AB.start()
    thread_BA.start()
    thread_AB.join()
    thread_BA.join()

    # Sockets will be closed in thread finally blocks
    tracer.info("All threads have terminated.")

    tracer.info("close socket A %d and B %d"% (socket_A.fileno(), socket_B.fileno()))
    socket_A.close()
    socket_B.close()



def hostValidator(string: str) -> tuple[str, int]:
    addr = string.split(':')

    if len(addr)>2:
        raise argparse.ArgumentTypeError("format must be [host:]port")
    elif len(addr) == 2:
        ipStr, portStr = addr
    else:
        ipStr = "localhost"
        portStr = addr[0]

    port = int(portStr)
    if not (0 < port < 65536):
        raise argparse.ArgumentTypeError(f"Port number {port} is out of the allowed range [1-65535]")
    return ipStr, port

def probabilityValidator(string: str) -> float:
    prob = float(string)

    if not (0 <= prob <= 1):
        raise argparse.ArgumentTypeError(f"probability {prob} is out of the allowed range [0-1]")
    return prob

description=\
'''
Character stream processor. It add 'noise' in the streams between two host.
It connects to two hosts (which must have been set up in advance).
Data flows from host A to B and vice versa, but is "processed" to simulate a noisy line

     ▲                                              ▲
     │                                              │
     │                                              │
     ▼            noise_injector_mte.py             ▼
┌─────────┐     ┌────────────────────────┐     ┌─────────┐
│         │     │                        │     │         │
│ HOST A  │◄────┼─────  add noise  ◄─────┼─────┤ HOST B  │
│         │     │                        │     │         │
│         │     │------------------------┤     │         │
│ ip:port │     │                        │     │ ip:port │
│         ├─────┼────►  add noise  ──────┼────►│         │
└─────────┘     │                        │     └─────────┘
                └────────────────────────┘

noise is randomly generated, and can be controlled with parameters.
The pseudorandom generators are independent for the two streams.

mte stands for Multi Thread Event
This is implemented using two thread, and using python events as signaling channel
'''

epilog=\
'''
Usage example:

socat TCP-LISTEN:9999,reuseaddr,fork pty,raw,echo=0,link=/tmp/ttyV1 &
socat TCP-LISTEN:10000,reuseaddr,fork pty,raw,echo=0,link=/tmp/ttyV2 &
python3 noise_injector.py -a 9999 -b 10000 --seed-AB 123456 --seed-BA 876543 --error-rate 0.002 --deletion_chance 0.15 &

The first line create a pty linked to /tmp/ttyV1, and in the other end a TCP server on port 9999
The second line create a pty linked to /tmp/ttyV2, and in the other end a TCP server on port 10000
The third line run noise_injector.py that connect to both TCP server

Now you can cat some into /tmp/ttyV1 and see them (corrupted) flowing out of /tmp/ttyV2

cat </tmp/ttyV1
cat >/tmp/ttyV2

For debug purposes you can run the three commands in three different terminal, using parameters "-dd -v -x" (just as example, on both socat and noise_injector.py) you can see some useful debug informations
'''


class SmartFormatter(argparse.HelpFormatter):
    """Formatter that respects user carriage returns and adapts text to console size."""

    def _split_lines(self, text, width):
        text_lines = text.splitlines()  # Splits the original text where there are '\n' added by the user
        wrapped_lines = []
        for line in text_lines:
            if line:  # If the line contains text, it formats it with respect to the width of the console
                wrapped_lines.extend(textwrap.wrap(line, width))
            else:  # Otherwise, it adds a blank line
                wrapped_lines.append('')
        return wrapped_lines

class Formatter(argparse.ArgumentDefaultsHelpFormatter, SmartFormatter, argparse.RawDescriptionHelpFormatter): pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=Formatter, description=description, epilog=epilog)
    parser.add_argument("-a", "--host-a", metavar='[hostA:]portA', help="HostA address. HostA is optional and can be an ip or hostname. If omitted hostA is 'localhost'", type=hostValidator, required=True)
    parser.add_argument("-b", "--host-b", metavar='[hostB:]portB', help="HostB address. HostB is optional and can be an ip or hostname. If omitted hostB is 'localhost'", type=hostValidator, required=True)
    parser.add_argument("--seed-AB", type=int, default=12345, help="Seed for pseudorandom generator that add noise to stream A->B")
    parser.add_argument("--seed-BA", type=int, default=23456, help="Seed for pseudorandom generator that add noise to stream B->A")
    parser.add_argument("--error-rate", type=probabilityValidator, help="Is the probability that a byte will be injected with an error.\nThis value is the reciprocal of the mean interval between the errors, i.e. the mean number of characters that pass untouched before inject en error. \n(range 0~1)", default=0.002)
    parser.add_argument("--deletion_chance", type=probabilityValidator, default=0.2, help="The probability that an error results in data deletion (range 0~1)")
    parser.add_argument("-d", "--debug", action='count', default=1, help="Increase debug level")
    parser.add_argument("-v", action="store_true", help="verbose text dump of data traffic")
    parser.add_argument("-x", action="store_true", help="verbose hexadecimal dump of data traffic")
    args = parser.parse_args()

    main(args)
