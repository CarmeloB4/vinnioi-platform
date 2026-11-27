# /// script
# requires-python = ">=3.12"
# dependencies = ["pyshp==2.3.1", "pyproj==3.7.2"]
# ///
"""Trasforma il sottoinsieme AG del file ISTAT, senza geocodificare interventi."""

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path

import shapefile
from pyproj import CRS, Transformer

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--archive", type=Path, required=True)
parser.add_argument(
    "--output", type=Path, default=Path("apps/web/public/data/municipalities.geojson")
)
args = parser.parse_args()
raw = args.archive.read_bytes()
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    stem = next(
        name[:-4] for name in archive.namelist() if name.startswith("Com") and name.endswith(".shp")
    )
    reader = shapefile.Reader(
        shp=io.BytesIO(archive.read(stem + ".shp")),
        dbf=io.BytesIO(archive.read(stem + ".dbf")),
        shx=io.BytesIO(archive.read(stem + ".shx")),
        encoding="utf-8",
    )
    transformer = Transformer.from_crs(
        CRS.from_wkt(archive.read(stem + ".prj").decode()), "EPSG:4326", always_xy=True
    )

    def convert(coords):
        if isinstance(coords[0], (int, float)):
            x, y = transformer.transform(*coords[:2])
            return [round(x, 5), round(y, 5)]
        return [convert(value) for value in coords]

    features = []
    for item in reader.iterShapeRecords():
        record = item.record.as_dict()
        code = str(record.get("PRO_COM_T", record.get("PRO_COM"))).zfill(6)
        if not code.startswith("084"):
            continue
        geometry = dict(item.shape.__geo_interface__)
        geometry["coordinates"] = convert(geometry["coordinates"])
        features.append(
            {
                "type": "Feature",
                "id": code,
                "properties": {"code": code, "name": record["COMUNE"]},
                "geometry": geometry,
            }
        )
assert len(features) == 43, f"Attesi 43 comuni, trovati {len(features)}"
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(
    json.dumps(
        {"type": "FeatureCollection", "features": features},
        separators=(",", ":"),
        ensure_ascii=False,
    )
    + "\n"
)
metadata = {
    "source": "ISTAT",
    "reference_date": "2026-01-01",
    "url": "https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati/2026/Limiti01012026_g.zip",
    "archive_sha256": hashlib.sha256(raw).hexdigest(),
    "geojson_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
    "license": "CC BY 4.0",
    "license_url": "https://www.istat.it/note-legali/",
    "attribution": (
        "Fonte: ISTAT, confini amministrativi generalizzati 2026; elaborazione Vinnioi: "
        "selezione AG, riproiezione EPSG:4326 e arrotondamento a 5 decimali. "
        "Confini ai soli fini statistici."
    ),
    "features": len(features),
}
args.output.with_suffix(".provenance.json").write_text(
    json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
)
print(f"{len(features)} comuni: {args.output.stat().st_size} byte")
