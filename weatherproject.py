# Standard library imports
import json
# Third-party library for HTTP requests (more user-friendly than urllib)
import requests

# Open-Meteo endpoint to look up the latitude/longitude for a city name
GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1/search'
# Open-Meteo endpoint to request weather forecast data
FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'

def fetch_json(url, params):
    """Send an HTTP GET request and parse JSON response using requests library."""
    try:
        # Use requests.get() to make the HTTP request
        # params dict is automatically converted to query string
        response = requests.get(url, params=params, timeout=20)
        # raise_for_status() raises an exception for HTTP error codes (4xx, 5xx)
        response.raise_for_status()
        # Return parsed JSON data
        return response.json()
    except requests.exceptions.Timeout:
        # Handle timeout errors (request took too long)
        raise RuntimeError(f"Request timed out after 20 seconds: {url}")
    except requests.exceptions.ConnectionError:
        # Handle network connection errors (no internet, DNS issues, etc.)
        raise RuntimeError(f"Connection error - check your internet connection: {url}")
    except requests.exceptions.HTTPError as e:
        # Handle HTTP errors (4xx, 5xx status codes)
        raise RuntimeError(f"HTTP error {response.status_code}: {response.reason} for {url}")
    except requests.exceptions.RequestException as e:
        # Catch any other requests-related errors
        raise RuntimeError(f"Request failed: {str(e)} for {url}")
    except ValueError as e:
        # Handle JSON parsing errors (if response isn't valid JSON)
        raise RuntimeError(f"Invalid JSON response from {url}: {str(e)}")


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

    # Loop until we get valid city and state input
    while True:
        # Get city input and remove whitespace
        city = input('Enter city name: ').strip()
        if not city:
            print('City cannot be empty. Please try again.')
            continue

        # Get state input and remove whitespace
        state = input('Enter state code or name (e.g. CA or California): ').strip()
        if not state:
            print('State cannot be empty. Please try again.')
            continue

        # Try to look up location in geocoding API
        try:
            loc = find_location(city, state)
        except RuntimeError as e:
            # Handle network/API errors with specific messages
            print(f'Network or API error: {e}')
            print('Please check your internet connection and try again.')
            continue
        except Exception as e:
            # Handle unexpected errors
            print(f'Unexpected error looking up location: {e}')
            print('Please try again.')
            continue

        # Retry if location not found
        if not loc:
            print(f'Could not find location for {city}, {state}. Please try again.')
            continue

        # Exit loop once valid location is found
        break

    # Extract location data from the dictionary
    name = loc.get('name')  # City name
    admin1 = loc.get('admin1') or ''  # State name
    country = loc.get('country') or ''  # Country
    lat = loc['latitude']  # Latitude
    lon = loc['longitude']  # Longitude
    tz = loc.get('timezone', 'auto')  # Timezone

    # Show location to user
    print(f'Found location: {name}, {admin1}, {country} ({lat}, {lon})')

    # Fetch 10-day forecast from API
    try:
        forecast = get_forecast(lat, lon, tz)
    except RuntimeError as e:
        # Handle network/API errors with specific messages
        print(f'Network or API error retrieving forecast: {e}')
        print('Please check your internet connection and try again later.')
        return
    except Exception as e:
        # Handle unexpected errors
        print(f'Unexpected error retrieving forecast: {e}')
        return

    # Extract daily forecast data (lists of dates, temps, precip, weather codes)
    daily = forecast.get('daily', {})
    dates = daily.get('time', [])  # List of dates
    tmax = daily.get('temperature_2m_max', [])  # Max temps in Celsius
    tmin = daily.get('temperature_2m_min', [])  # Min temps in Celsius
    precip = daily.get('precipitation_sum', [])  # Precip in millimeters
    weathercode = daily.get('weathercode', [])  # Weather codes

    # Validate that forecast data was returned
    if not dates:
        print('No daily forecast data returned.')
        return

    # Print table header and data rows
    print('\nDate       | Min (°F) | Max (°F) | Precip (in) | Weather Code')
    print('-----------------------------------------------------------')
    # Loop through each day and convert units
    for i, date in enumerate(dates):
        min_f = c_to_f(tmin[i])  # Convert min temp to Fahrenheit
        max_f = c_to_f(tmax[i])  # Convert max temp to Fahrenheit
        precip_in = mm_to_inches(precip[i])  # Convert precip to inches
        print(f"{date} | {min_f:>8.1f} | {max_f:>8.1f} | {precip_in:>10.2f} | {weathercode[i]}")

    # Print final message before exit
    print('\nDone. Application will terminate.')

if __name__ == '__main__':
    main()
