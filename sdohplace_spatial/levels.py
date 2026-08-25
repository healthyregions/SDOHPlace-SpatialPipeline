"""Census level metadata. Lambda spatial_level is `bg` (not `blockgroup`)."""

from sdohplace_spatial.errors import PipelineError

LEVELS = {
    "state": {
        "prefix": "040US",
        "id_length": 2,
        "shp_url": "https://herop-geodata.s3.us-east-2.amazonaws.com/oeps/state-2018-500k-shp.zip",
    },
    "county": {
        "prefix": "050US",
        "id_length": 5,
        "shp_url": "https://herop-geodata.s3.us-east-2.amazonaws.com/oeps/county-2018-500k-shp.zip",
    },
    "tract": {
        "prefix": "140US",
        "id_length": 11,
        "shp_url": "https://herop-geodata.s3.us-east-2.amazonaws.com/oeps/tract-2018-500k-shp.zip",
    },
    "bg": {
        "prefix": "150US",
        "id_length": 12,
        "shp_url": "https://herop-geodata.s3.us-east-2.amazonaws.com/oeps/bg-2018-500k-shp.zip",
    },
    "zcta": {
        "prefix": "860US",
        "id_length": 5,
        "shp_url": "https://herop-geodata.s3.us-east-2.amazonaws.com/oeps/zcta-2018-500k-shp.zip",
    },
}

CENSUS_LENGTHS = {2, 5, 11, 12}


def normalize_spatial_level(spatial_level: str | None) -> str:
    if spatial_level == "blockgroup":
        return "bg"
    if spatial_level not in LEVELS:
        raise PipelineError(
            "unreadable_file",
            "spatial_level must be one of: state, county, tract, bg, zcta.",
        )
    return spatial_level
