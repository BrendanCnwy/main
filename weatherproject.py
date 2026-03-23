# Standard library imports for making HTTP requests and working with JSON
import json
import urllib.parse
import urllib.request

# Open-Meteo endpoint to look up the latitude/longitude for a city name
GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1/search'
# Open-Meteo endpoint to request weather forecast data
FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'

def fetch_json(url, params):
    """Send an HTTP GET request and parse JSON response."""
    # Build query string from input parameters (dictionary of key/value pairs)
    query = urllib.parse.urlencode(params)
    full_url = f"{url}?{query}"

    # Open URL and read JSON response. Raises on HTTP errors.
    with urllib.request.urlopen(full_url, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status} from {full_url}")
        return json.load(response)


def find_location(city, state):
    """Find best match location from geocoding API using city + state."""

    # Query up to 10 candidate locations
    params = {'name': city, 'count': 10, 'language': 'en', 'format': 'json'}
    data = fetch_json(GEOCODING_URL, params)

    # If no results, return None so calling code can retry
    if not data.get('results'):
        return None

    # Normalize state for comparison (lowercase, trimmed spaces)
    state_norm = state.strip().lower()

    # Prefer exact admin1 match (typically state name) first
    for item in data['results']:
        admin1 = (item.get('admin1') or '').strip().lower()
        if state_norm and admin1 == state_norm:
            return item

    # If not exact, prefer United States match next
    for item in data['results']:
        if item.get('country_code', '').lower() == 'us':
            return item

    # Last fallback to the first result
    return data['results'][0]

def get_forecast(lat, lon, timezone):
    """Retrieve 10-day forecast for given coordinates and timezone."""
    params = {
        'latitude': lat,
        'longitude': lon,
        # Request daily data fields: max/min temperature, precipitation, weather code
        'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode',
        'timezone': timezone,
        'forecast_days': 10,
    }
    return fetch_json(FORECAST_URL, params)


def c_to_f(celsius):
    """Convert Celsius temperature to Fahrenheit."""
    # Fahrenheit formula = (°C * 9/5) + 32
    return celsius * 9.0 / 5.0 + 32.0


def mm_to_inches(mm):
    """Convert millimeters of precipitation to inches."""
    # 25.4 millimeters = 1 inch
    return mm / 25.4


def main():
    """Main program flow:
    1. Prompt user for city and state (with repeat retries for invalid input)
    2. Find location using geocoding API
    3. Request 10-day forecast for the matched location
    4. Convert units to US imperial and print results
    """
    print('10-Day Weather Forecast (Open-Meteo API)')

    # Keep asking until we have a location match to proceed
    while True:
        city = input('Enter city name: ').strip()
        if not city:
            print('City cannot be empty. Please try again.')
            continue

        state = input('Enter state code or name (e.g. CA or California): ').strip()
        if not state:
            print('State cannot be empty. Please try again.')
            continue

        try:
            loc = find_location(city, state)
        except Exception as e:
            print(f'Error looking up location: {e}')
            print('Please try again.')
            continue

        if not loc:
            print(f'Could not find location for {city}, {state}. Please try again.')
            continue

        break

    name = loc.get('name')
    admin1 = loc.get('admin1') or ''
    country = loc.get('country') or ''
    lat = loc['latitude']
    lon = loc['longitude']
    tz = loc.get('timezone', 'auto')

    print(f'Found location: {name}, {admin1}, {country} ({lat}, {lon})')

    try:
        forecast = get_forecast(lat, lon, tz)
    except Exception as e:
        print(f'Error retrieving forecast: {e}')
        return

    daily = forecast.get('daily', {})
    dates = daily.get('time', [])
    tmax = daily.get('temperature_2m_max', [])
    tmin = daily.get('temperature_2m_min', [])
    precip = daily.get('precipitation_sum', [])
    weathercode = daily.get('weathercode', [])

    if not dates:
        print('No daily forecast data returned.')
        return

    print('\nDate       | Min (°F) | Max (°F) | Precip (in) | Weather Code')
    print('-----------------------------------------------------------')
    for i, date in enumerate(dates):
        min_f = c_to_f(tmin[i])
        max_f = c_to_f(tmax[i])
        precip_in = mm_to_inches(precip[i])
        print(f"{date} | {min_f:>8.1f} | {max_f:>8.1f} | {precip_in:>10.2f} | {weathercode[i]}")

    print('\nDone. Application will terminate.')

if __name__ == '__main__':
    main()
