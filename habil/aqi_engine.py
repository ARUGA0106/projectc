EPA_BREAKPOINTS = {
    "pm2_5": [
        (0.0, 12.0, 0, 50, "Good", "#00e400"),
        (12.1, 35.4, 51, 100, "Moderate", "#ffff00"),
        (35.5, 55.4, 101, 150, "Unhealthy for Sensitive Groups", "#ff7e00"),
        (55.5, 150.4, 151, 200, "Unhealthy", "#ff0000"),
        (150.5, 250.4, 201, 300, "Very Unhealthy", "#8f3f97"),
        (250.5, 500.4, 301, 500, "Hazardous", "#7e0023")
    ],
    "pm10": [
        (0, 54, 0, 50, "Good", "#00e400"),
        (55, 154, 51, 100, "Moderate", "#ffff00"),
        (155, 254, 101, 150, "Unhealthy for Sensitive Groups", "#ff7e00"),
        (255, 354, 151, 200, "Unhealthy", "#ff0000"),
        (355, 424, 201, 300, "Very Unhealthy", "#8f3f97"),
        (425, 604, 301, 500, "Hazardous", "#7e0023")
    ],
    "co": [
        (0.0, 4.4, 0, 50, "Good", "#00e400"),
        (4.5, 9.4, 51, 100, "Moderate", "#ffff00"),
        (9.5, 12.4, 101, 150, "Unhealthy for Sensitive Groups", "#ff7e00"),
        (12.5, 15.4, 151, 200, "Unhealthy", "#ff0000"),
        (15.5, 30.4, 201, 300, "Very Unhealthy", "#8f3f97"),
        (30.5, 50.4, 301, 500, "Hazardous", "#7e0023")
    ],
    "nh3": [
        (0, 200, 0, 50, "Good", "#00e400"),
        (201, 400, 51, 100, "Satisfactory", "#ffff00"),
        (401, 800, 101, 200, "Moderately Polluted", "#ff7e00"),
        (801, 1200, 201, 300, "Poor", "#ff0000"),
        (1201, 1800, 301, 400, "Very Poor", "#8f3f97"),
        (1801, float('inf'), 401, 500, "Severe", "#7e0023")
    ],
}

def calculate_aqi(pollutant, concentration):
    breakpoints = EPA_BREAKPOINTS.get(pollutant.lower())
    if not breakpoints:
        return None
    for c_lo, c_hi, i_lo, i_hi, category, color in breakpoints:
        if c_lo <= concentration <= c_hi:
            aqi = ((i_hi - i_lo) / (c_hi - c_lo)) * (concentration - c_lo) + i_lo
            return {
                "pollutant": pollutant,
                "concentration": concentration,
                "aqi": round(aqi),
                "category": category,
                "color": color
            }
    return {
        "pollutant": pollutant,
        "concentration": concentration,
        "aqi": None,
        "category": "Out of Range",
        "color": "#808080"
    }