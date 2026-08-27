"""State FIPS → name. Copied (not imported) from the manager lookup. Do not use for geometry."""

# 50 states + DC. Territories stay in STATE_FP_LOOKUP but are not required for "United States".
STATE_FP_LOOKUP = {
    "01": "Alabama",
    "02": "Alaska",
    "04": "Arizona",
    "05": "Arkansas",
    "06": "California",
    "08": "Colorado",
    "09": "Connecticut",
    "10": "Delaware",
    "11": "District of Columbia",
    "12": "Florida",
    "13": "Georgia",
    "15": "Hawaii",
    "16": "Idaho",
    "17": "Illinois",
    "18": "Indiana",
    "19": "Iowa",
    "20": "Kansas",
    "21": "Kentucky",
    "22": "Louisiana",
    "23": "Maine",
    "24": "Maryland",
    "25": "Massachusetts",
    "26": "Michigan",
    "27": "Minnesota",
    "28": "Mississippi",
    "29": "Missouri",
    "30": "Montana",
    "31": "Nebraska",
    "32": "Nevada",
    "33": "New Hampshire",
    "34": "New Jersey",
    "35": "New Mexico",
    "36": "New York",
    "37": "North Carolina",
    "38": "North Dakota",
    "39": "Ohio",
    "40": "Oklahoma",
    "41": "Oregon",
    "42": "Pennsylvania",
    "72": "Puerto Rico",
    "44": "Rhode Island",
    "45": "South Carolina",
    "46": "South Dakota",
    "47": "Tennessee",
    "48": "Texas",
    "49": "Utah",
    "50": "Vermont",
    "51": "Virginia",
    "78": "Virgin Islands",
    "53": "Washington",
    "54": "West Virginia",
    "55": "Wisconsin",
    "56": "Wyoming",
}

TERRITORY_FIPS = frozenset({"72", "78"})
NATIONAL_FIPS = frozenset(STATE_FP_LOOKUP) - TERRITORY_FIPS
CONUS_FIPS = NATIONAL_FIPS - {"02", "15"}


def state_fips_from_herop_id(herop_id: str, spatial_level: str) -> str | None:
    """GEOID after US: state / county / tract / bg start with 2-digit state FIPS. ZCTA does not."""
    text = str(herop_id).strip().upper()
    if spatial_level == "zcta" or "US" not in text:
        return None
    geoid = text.split("US", 1)[1]
    if len(geoid) < 2:
        return None
    return geoid[:2]
