from dingolytics.presets import PresetLoader


def test_presets_loader(presets_dir):
    presets = PresetLoader(base_path=presets_dir)
    presets.load_all()
    assert len(presets) == 1
    assert presets["fakedb"]
    assert presets["fakedb"]["dummy"]
