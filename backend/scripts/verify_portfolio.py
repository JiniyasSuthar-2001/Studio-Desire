import urllib.request
import json

def verify():
    url = "http://localhost:8000/api/projects"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        print(f"PASS: /api/projects status 200, total={data['total']}")
        
        # Verify each project has required metadata
        for p in data["projects"]:
            assert p["id"] is not None
            assert p["title"]
            assert p["slug"]
            assert p["category"]
            assert p["cover_image"]
            print(f"  - [{p['category']}] {p['title']} ({p.get('project_type') or 'N/A'}) - {p['location']}")

        # Verify no test project leaked
        titles = [p["title"] for p in data["projects"]]
        assert not any("Public Project with Mixed Media" in t for t in titles)
        assert not any("Secret Unpublished Villa" in t for t in titles)
        print("PASS: Zero test/unpublished projects in public response")

        # Verify single project endpoint
        slug = data["projects"][0]["slug"]
        single_url = f"http://localhost:8000/api/projects/{slug}"
        with urllib.request.urlopen(single_url) as s_resp:
            assert s_resp.status == 200
            s_data = json.loads(s_resp.read().decode("utf-8"))
            assert s_data["slug"] == slug
            print(f"PASS: /api/projects/{slug} status 200, media_count={len(s_data['media'])}")

        # Verify hospitality projects category
        hospitality_projs = [p for p in data["projects"] if p["category"] == "Hospitality"]
        print(f"PASS: Found {len(hospitality_projs)} Hospitality projects: {[p['title'] for p in hospitality_projs]}")

if __name__ == "__main__":
    verify()
