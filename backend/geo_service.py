"""
IP Geolocation Service for Audit Logs
Provides two-tier geolocation: MaxMind GeoLite2 (primary) and ip-api.com (fallback)
"""
import os
import requests
from functools import lru_cache

# Try to import geoip2 (optional dependency)
try:
    import geoip2.database
    GEOIP2_AVAILABLE = True
except ImportError:
    GEOIP2_AVAILABLE = False
    print("Warning: geoip2 not installed. Using online API only for IP geolocation.")


class GeoLocationService:
    """Service for resolving IP addresses to geographic locations"""

    def __init__(self, maxmind_db_path=None):
        """
        Initialize geolocation service

        Args:
            maxmind_db_path: Path to MaxMind GeoLite2-City.mmdb file
        """
        self.maxmind_db_path = maxmind_db_path or os.getenv('MAXMIND_DB_PATH', '/usr/share/GeoIP/GeoLite2-City.mmdb')
        self.reader = None

        # Try to initialize MaxMind reader if available
        if GEOIP2_AVAILABLE and os.path.exists(self.maxmind_db_path):
            try:
                self.reader = geoip2.database.Reader(self.maxmind_db_path)
                print(f"MaxMind GeoIP2 database loaded from {self.maxmind_db_path}")
            except Exception as e:
                print(f"Warning: Could not load MaxMind database: {e}")

    @lru_cache(maxsize=1000)
    def geolocate(self, ip_address):
        """
        Get geolocation for an IP address

        Args:
            ip_address: IP address to geolocate

        Returns:
            dict: {
                'country': 'US',
                'country_name': 'United States',
                'city': 'New York',
                'region': 'NY',
                'latitude': 40.7128,
                'longitude': -74.0060,
                'timezone': 'America/New_York',
                'source': 'maxmind' or 'ip-api'
            }
            Returns None if geolocation fails
        """
        if not ip_address or ip_address in ['127.0.0.1', 'localhost', '::1']:
            return {
                'country': 'Local',
                'country_name': 'Localhost',
                'city': 'Local',
                'region': '',
                'latitude': 0,
                'longitude': 0,
                'timezone': 'UTC',
                'source': 'localhost'
            }

        # Try MaxMind first (fast, offline)
        if self.reader:
            try:
                response = self.reader.city(ip_address)
                return {
                    'country': response.country.iso_code or '',
                    'country_name': response.country.name or '',
                    'city': response.city.name or '',
                    'region': response.subdivisions.most_specific.iso_code if response.subdivisions else '',
                    'latitude': response.location.latitude,
                    'longitude': response.location.longitude,
                    'timezone': response.location.time_zone or 'UTC',
                    'source': 'maxmind'
                }
            except Exception as e:
                print(f"MaxMind lookup failed for {ip_address}: {e}")

        # Fallback to ip-api.com (online, free tier: 45 req/min)
        try:
            response = requests.get(
                f'http://ip-api.com/json/{ip_address}',
                params={'fields': 'status,country,countryCode,region,city,lat,lon,timezone'},
                timeout=2
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return {
                        'country': data.get('countryCode', ''),
                        'country_name': data.get('country', ''),
                        'city': data.get('city', ''),
                        'region': data.get('region', ''),
                        'latitude': data.get('lat', 0),
                        'longitude': data.get('lon', 0),
                        'timezone': data.get('timezone', 'UTC'),
                        'source': 'ip-api'
                    }
        except Exception as e:
            print(f"IP-API lookup failed for {ip_address}: {e}")

        # Return unknown if all methods fail
        return {
            'country': 'Unknown',
            'country_name': 'Unknown',
            'city': 'Unknown',
            'region': '',
            'latitude': 0,
            'longitude': 0,
            'timezone': 'UTC',
            'source': 'unknown'
        }

    def get_country_flag_emoji(self, country_code):
        """
        Convert ISO country code to flag emoji

        Args:
            country_code: Two-letter ISO country code (e.g., 'US', 'GB')

        Returns:
            str: Flag emoji (e.g., '🇺🇸', '🇬🇧')
        """
        if not country_code or len(country_code) != 2:
            return '🏳️'

        # Convert to regional indicator symbols
        # A=🇦 (127462), B=🇧 (127463), etc.
        return ''.join(chr(127397 + ord(c)) for c in country_code.upper())

    def __del__(self):
        """Close MaxMind database reader on cleanup"""
        if self.reader:
            try:
                self.reader.close()
            except:
                pass


# Global instance
_geo_service = None

def get_geo_service():
    """Get or create global GeoLocationService instance"""
    global _geo_service
    if _geo_service is None:
        _geo_service = GeoLocationService()
    return _geo_service


# Convenience functions
def geolocate_ip(ip_address):
    """Geolocate an IP address"""
    return get_geo_service().geolocate(ip_address)


def get_country_flag(country_code):
    """Get flag emoji for country code"""
    return get_geo_service().get_country_flag_emoji(country_code)
