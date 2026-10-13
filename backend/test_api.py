import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def run_tests():
    print("Testing /api/health...")
    r = client.get("/api/health")
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    print("Health check OK:", r.json())

    print("\nTesting GET /api/projects...")
    r = client.get("/api/projects")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 0
    assert "projects" in data and isinstance(data["projects"], list)
    print(f"Retrieved {data['total']} projects successfully.")

    print("\nTesting GET /api/projects/featured...")
    r = client.get("/api/projects/featured")
    assert r.status_code == 200
    featured = r.json()
    assert featured["featured"] is True
    print(f"Featured project: {featured['title']} ({featured['location']})")

    print("\nTesting GET /api/projects?category=Residential...")
    r = client.get("/api/projects?category=Residential")
    assert r.status_code == 200
    res_data = r.json()
    print(f"Residential count: {res_data['total']}")
    assert all(p["category"].lower() == "residential" for p in res_data["projects"])

    print("\nTesting GET /api/projects?media_type=video...")
    r = client.get("/api/projects?media_type=video")
    assert r.status_code == 200
    vid_data = r.json()
    print(f"Video projects count: {vid_data['total']}")
    assert vid_data["total"] > 0

    print("\nTesting GET /api/projects/residence-01...")
    r = client.get("/api/projects/residence-01")
    assert r.status_code == 200
    detail = r.json()
    assert len(detail["media"]) > 0
    print(f"Residence 01 retrieved with {len(detail['media'])} media items.")

    print("\nTesting 404 for unknown project...")
    r = client.get("/api/projects/unknown-slug-xyz")
    assert r.status_code == 404
    print("404 handled properly:", r.json())

    print("\nAll Backend API Tests Passed Successfully!")

if __name__ == "__main__":
    run_tests()
