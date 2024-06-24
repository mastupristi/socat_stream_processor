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
import random
import signal
import sys
import textwrap
from tracer import create_tracer
from dataTracer import dataTracer
import select



# Gestione del segnale di interruzione (Ctrl+C)
def signal_handler(signal_sock :list, tracer):
    """Sends a shutdown signal to all threads via the signal socket."""
    tracer.info("Signal received, stopping threads...")
    signal_sock.sendall(b'stop')

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

def handle_connection(socket_A, socket_B, signal_sock, seed_AB, seed_BA, error_rate, deletion_chance, verbose, hexadecimal, tracer):
    """Handles data transfer and listens for shutdown signals."""
    outgoingByte = 0
    tracer.debug("A->B Random numnber generator seeded with %d" %seed_AB)
    tracer.debug("B->A Random numnber generator seeded with %d" %seed_BA)
    rng_AB = random.Random(seed_AB)
    rng_BA = random.Random(seed_BA)
    try:
        while True:
            rlist, _, _ = select.select([socket_A, socket_B, signal_sock], [], [])
            for ready_sock in rlist:
                if ready_sock is signal_sock:
                    signal = signal_sock.recv(1024)
                    if signal == b'stop':
                        tracer.info("Stop signal received")
                        return  # Exit the thread if stop signal is received
                elif ready_sock is socket_A:
                    data = socket_A.recv(1024)
                    if not data:
                        raise Exception("No data received, possibly disconnected")
                    disturbed_data = disturb(data, error_rate, deletion_chance, rng_AB)
                    dataDump(disturbed_data, verbose, hexadecimal, '>', len(disturbed_data), outgoingByte)
                    outgoingByte += len(disturbed_data)
                    socket_B.sendall(disturbed_data)
                elif ready_sock is socket_B:
                    data = socket_B.recv(1024)
                    if not data:
                        raise Exception("No data received, possibly disconnected")
                    disturbed_data = disturb(data, error_rate, deletion_chance, rng_BA)
                    dataDump(disturbed_data, verbose, hexadecimal, '<', len(disturbed_data), outgoingByte)
                    outgoingByte += len(disturbed_data)
                    socket_A.sendall(disturbed_data)

    except Exception as e:
        tracer.error(f"Error in thread: {e}")


def main(args):

    tracer = create_tracer(__name__, args.debug)
    tracer.info("Starting")
    # Prepare connections
    socket_A = socket.create_connection((*args.host_a,))
    socket_B = socket.create_connection((*args.host_b,))

    tracer.info("Socket created A %d and B %d" % (socket_A.fileno(), socket_B.fileno()))

    signal_sock_src, signal_sock_dst = socket.socketpair()

    signal.signal(signal.SIGINT, lambda s, f: signal_handler(signal_sock_src, tracer))

    handle_connection(socket_A, socket_B, signal_sock_dst, args.seed_AB, args.seed_BA, args.error_rate, args.deletion_chance, args.v, args.x, tracer)

    tracer.info("close socket A %d and B %d"% (socket_A.fileno(), socket_B.fileno()))
    socket_A.close()
    socket_B.close()
    signal_sock_src.close()
    signal_sock_dst.close()



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
     ▼            noise_injector_sts.py             ▼
┌─────────┐     ┌────────────────────────┐     ┌─────────┐
│         │     │                        │     │         │
│ HOST A  │◄────┼───                  ◄──┼─────┤ HOST B  │
│         │     │                        │     │         │
│         │     │       add noise        │     │         │
│ ip:port │     │                        │     │ ip:port │
│         ├─────┼──►                  ───┼────►│         │
└─────────┘     │                        │     └─────────┘
                └────────────────────────┘

noise is randomly generated, and can be controlled with parameters.
The pseudorandom generators are independent for the two streams.

sts stands for Single Thread Socket
This is implemented using one thread, and using another socket as signaling channel
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
