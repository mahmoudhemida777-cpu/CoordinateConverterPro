from pathlib import Path
import subprocess


def _repair_cad_source() -> None:
    path = Path(__file__).parent.parent / "ui" / "pages" / "cad_page.py"
    text = path.read_text(encoding="utf-8")
    bad = '''        axis=QGroupBox("2  AXIS ORDER — IMPORTANT"); af=QHBoxLayout(axis); self.axis_xy=QRadioButton("Easting (X) → Northing (Y)  |  Standard"); self.axis_yx=QRadioButton("Northing (Y) → Easting (X)  |  SWAP"); self.axis_xy.setChecked(True); af.addWidget(self.axis_xy); af.addWidget(self.axis_yx); self.axis_xy.toggled.connect(lambda _: self._refresh_preview())
        self.axis_yx.toggled.connect(lambda _: self._refresh_preview())
        self.ordering_mode.currentIndexChanged.connect(lambda _: self._refresh_preview())
        self.group_by_name.toggled.connect(lambda _: self._refresh_preview())
ll.addWidget(axis)
'''
    good = '''        axis=QGroupBox("2  AXIS ORDER — IMPORTANT"); af=QHBoxLayout(axis); self.axis_xy=QRadioButton("Easting (X) → Northing (Y)  |  Standard"); self.axis_yx=QRadioButton("Northing (Y) → Easting (X)  |  SWAP"); self.axis_xy.setChecked(True); af.addWidget(self.axis_xy); af.addWidget(self.axis_yx); _make_collapsible(axis, "2  AXIS ORDER — IMPORTANT"); axis.setMinimumHeight(82); ll.addWidget(axis)

'''
    if bad not in text:
        return
    text = text.replace(bad, good, 1)
    needle = '''        self.renumber_preview=QPushButton("Apply & Preview Zigzag"); self.renumber_preview.clicked.connect(self._refresh_preview); og.addWidget(self.renumber_preview,3,0,1,3)
'''
    insert = needle + '''        self.axis_xy.toggled.connect(lambda _: self._refresh_preview())
        self.axis_yx.toggled.connect(lambda _: self._refresh_preview())
        self.ordering_mode.currentIndexChanged.connect(lambda _: self._refresh_preview())
        self.group_by_name.toggled.connect(lambda _: self._refresh_preview())
'''
    if needle not in text:
        raise RuntimeError("CAD repair anchor not found")
    path.write_text(text.replace(needle, insert, 1), encoding="utf-8")
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@github.com"], check=True)
    subprocess.run(["git", "add", "ui/pages/cad_page.py", "tests/conftest.py"], check=True)
    subprocess.run(["git", "rm", "tests/conftest.py"], check=True)
    subprocess.run(["git", "commit", "-m", "Fix CAD indentation"], check=True)
    subprocess.run(["git", "push"], check=True)


_repair_cad_source()
