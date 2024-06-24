# Socat stream processor

The main purpose of this project is didactic, to learn (better) python, learn programming techniques needed in the various use cases that sim arise from time to time, learn how to use `socat` better, etc.

This repository contains some stream processors. Their main scope of use is together with `socat`. However, stream processors act on TCP streams, so they can be used in any domain where this mode of communication is used.
A stream processor means something that takes a stream and processes it in various ways.

## Project origin

I often used `socat` to simulate serial connections. The idea for one such stream processor came about when I needed to simulate a noisy serial line.
I've tried to combine this with the need/want to learn more and more Python (this explains why you will see the same steram processor implemented in multiple ways)

## Connection topology

Two instances of `socat` are used, each of which creates a device pty and acts as a TCP server. The stream processor will connect to these two TCP servers and start processing traffic in the two directions.

### Noise injector

This stream processor is the progenitor. It involves injecting "noise" onto streams in both directions.

The commands are `noise_injector_*.py`

The noise introduced can change a bit or remove an entire character. The `--error-rate` parameter dictates the probability of a character having an error or not. In fact, this corriusponds to the reciprocal of the average of consecutive characters without errors.<br>
When it is decided that a character has an error, there is another choice: is it a _bit error_ or is the _character deleted_? For this there is the `--deletion_chance` parameter, which imposes the probability that the error is a deletion type.<br>
In case the error is bit error, then a random bit among the 8 of the character is reversed.<br>
There are other parameters to set the seed of random generators (one per direction), for verbosity level (the same of `socat`), etc.

The command help is there for that purpose.

There are 3 implementations of this:
- **mte**: two threads and python events per signaling
- **mts**: two threads and socket for signaling
- **sts**: single thread and socket for signaling

#### Examples

- In terminal one:
  ```
  socat -d -d -x -v TCP-LISTEN:9999,reuseaddr,fork pty,raw,echo=0,link=/tmp/ttyV1
  ```
  `-d -d -x -v` are optional, used for trace<br>
  This creates `/tmp/ttyV1` as a serial device and it listen on TCP port 9999 for incoming connection

- In terminal two:
  ```
  socat -d -d -x -v TCP-LISTEN:10000,reuseaddr,fork pty,raw,echo=0,link=/tmp/ttyV2
  ```
  This creates `/tmp/ttyV2` as a serial device and it listen on TCP port 10000 for incoming connection

- In termnal three:
  ```
  python3 noise_injector_mts.py -a 9999 -b 10000 --seed-AB 123456 --seed-BA 876543 --error-rate 0.002 --deletion_chance 0.15 -dddd -v -x
  ```
  `-dddd -v -x` are optional, used for trace<br>
  This starts the stream processor that connects to TCP ports 9999 and 10000, and from here on it will process the traffic by injecting noise with the given parameters

At this point it's possible from one terminal to run `cat </tmp/tyyV2` and in another `cat >/tmp/tyyV1` and start typing characters on the keyboard and see what happens.

## Further processors

I would like to write a stream processor to implement an encrypted channel. A sort of TLS but over serial. Right now I wouldn't know where to start, I don't know if there is something already done, I don't know how to exchange keys at the beginning of the session (I was thinking Diffie-Hellman), etc.<br>
If you have any suggestions please share them.

Ideas for other stream processors can come, or you can suggest them to me, or you can also contribute.

## License

The project is covered by the Apache 2.0 license
