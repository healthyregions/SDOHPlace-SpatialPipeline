"""Census level metadata. Lambda spatial_level is `bg` (not `blockgroup`)."""

from sdohplace_spatial.errors import PipelineError

OEPS_SHP_TEMPLATE = (
    "https://herop-geodata.s3.us-east-2.amazonaws.com/oeps/{level}-{year}-500k-shp.zip"
)
SUPPORTED_BOUNDARY_YEARS = (2010, 2018)

LEVELS = {
    "state": {
        "prefix": "040US",
        "id_length": 2,
    },
    "county": {
        "prefix": "050US",
        "id_length": 5,
    },
    "tract": {
        "prefix": "140US",
        "id_length": 11,
    },
    "bg": {
        "prefix": "150US",
        "id_length": 12,
    },
    "zcta": {
        "prefix": "860US",
        "id_length": 5,
    },
}

CENSUS_LENGTHS = {2, 5, 11, 12}


def shapefile_url(spatial_level: str, year: int) -> str:
    return OEPS_SHP_TEMPLATE.format(level=spatial_level, year=year)


def normalize_spatial_level(spatial_level: str | None) -> str:
    if spatial_level == "blockgroup":
        return "bg"
    if spatial_level not in LEVELS:
        raise PipelineError(
            "unreadable_file",
            "spatial_level must be one of: state, county, tract, bg, zcta.",
        )
    return spatial_level
