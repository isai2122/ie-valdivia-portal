import requests
import json

BASE_URL = "http://localhost:8001/api"

def test():
    # 1. Login
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email":"admin@metanosrgan.co", "password":"Admin123!"})
    token = login_resp.json()['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Recurrence
    print("--- Recurrence Analysis ---")
    resp = requests.get(f"{BASE_URL}/trpc/analytics.recurrence", headers=headers)
    result = resp.json()['result']
    print(f"Total Real Events: {result['total_real_events']}")
    print(f"Top Station: {result['station_recurrence_ranking'][0]['station']} ({result['station_recurrence_ranking'][0]['event_count']} events)")
    
    # 3. GeoJSON
    print("\n--- GeoJSON Export ---")
    resp = requests.get(f"{BASE_URL}/trpc/export.geojson", headers=headers)
    result = resp.json()['result']
    print(f"GeoJSON Features: {len(result['features'])}")
    print(f"First Feature Coords: {result['features'][0]['geometry']['coordinates']}")

if __name__ == "__main__":
    test()
