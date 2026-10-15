from app.modules.relay.speed_meter import SpeedMeter


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_speed_is_zero_without_data():
    assert SpeedMeter(clock=FakeClock()).speed == 0


def test_speed_averages_over_window():
    clock = FakeClock()
    meter = SpeedMeter(window_seconds=3.0, clock=clock)

    for _ in range(3):
        clock.now += 1.0
        meter.add(3_000_000)

    assert meter.speed == 3_000_000


def test_fresh_stream_is_not_divided_by_full_window():
    clock = FakeClock()
    meter = SpeedMeter(window_seconds=3.0, clock=clock)

    clock.now += 1.0
    meter.add(2_000_000)

    assert meter.speed == 2_000_000


def test_first_burst_does_not_explode():
    clock = FakeClock()
    meter = SpeedMeter(window_seconds=3.0, clock=clock)

    clock.now += 0.01
    meter.add(1_000_000)

    # Az első másodpercben legalább 1 mp-cel osztunk.
    assert meter.speed == 1_000_000


def test_old_data_falls_out_of_window():
    clock = FakeClock()
    meter = SpeedMeter(window_seconds=3.0, clock=clock)

    clock.now += 1.0
    meter.add(9_000_000)
    clock.now += 10.0

    assert meter.speed == 0


def test_chunks_in_same_bucket_are_summed():
    clock = FakeClock()
    meter = SpeedMeter(window_seconds=3.0, clock=clock)

    clock.now += 5.0
    for _ in range(10):
        clock.now += 0.01
        meter.add(300_000)

    assert meter.speed == 1_000_000
