# Arduino Brain CSV bridge

PackScope supports the documented CSV layout emitted by `readCSV()` from the [kitschpatrol Brain library](https://github.com/kitschpatrol/Brain):

```text
signal_quality,attention,meditation,delta,theta,low_alpha,high_alpha,low_beta,high_beta,low_gamma,mid_gamma
```

Begin with the upstream `BrainSerialTest` or `BrainSoftSerialTest` example so that the hardware modification, voltage levels, and UART configuration remain under the operator's control. Configure the serial baud rate to match the `Serial.begin(...)` value in the sketch. BrainGrapher's sample Processing sketch uses 9600 baud, which is PackScope's Arduino bridge default.[1]

The PackScope integration consumes the Arduino's USB serial output. It does not require or redistribute the Arduino Brain library, which is LGPL-3.0. It records these values as device-derived relative bands and accepts the library's documented semantics: `0` signal-quality means good connection and `200` means no signal. A CSV bridge cannot expose bilateral F3/F4 EEG channels.[2]

## Quick validation

```bash
python -m pip install -e '.[serial]'
python examples/parse_mindflex_arduino.py --port /dev/ttyACM0 --baud 9600
```

Start with a short monitored session and confirm that the `signal_quality` field is consistently near zero before retaining any data. Do not derive design conclusions from Attention, Meditation, or a single band snapshot.

## References

[1]: https://github.com/kitschpatrol/brain-grapher "kitschpatrol BrainGrapher"
[2]: https://github.com/kitschpatrol/Brain "kitschpatrol Brain Arduino Library"
