# api_explorer.py
# This script helps find the correct API routes

import asyncio
import httpx


async def explore_api():
    base_url = "https://testbackend.educify.org"
    
    print("🔍 Exploring API Routes...")
    print("=" * 60)
    
    # Common API path variations to try
    possible_paths = [
        "/api",
        "/api/v1",
        "/api/v2",
        "/v1",
        "",  # Root
    ]
    
    # Common endpoint variations
    endpoints_to_try = [
        ("students", ["students/12345", "student/12345", "users/12345"]),
        ("teachers", ["teachers", "teacher", "tutors", "instructors"]),
        ("match", ["match", "matches", "matching"]),
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # First, try to get API documentation or root
        print("\n📋 Checking for API documentation...")
        doc_paths = ["/docs", "/api/docs", "/swagger", "/api-docs", "/", "/api"]
        
        for path in doc_paths:
            try:
                response = await client.get(f"{base_url}{path}")
                if response.status_code == 200:
                    print(f"   ✅ Found documentation at: {base_url}{path}")
                    print(f"      (Open this in your browser to see all routes)")
                    break
            except:
                pass
        
        print("\n🔍 Testing route combinations...")
        print("-" * 60)
        
        found_routes = []
        
        for api_path in possible_paths:
            for endpoint_name, variations in endpoints_to_try:
                for variation in variations:
                    url = f"{base_url}{api_path}/{variation}"
                    
                    try:
                        # Try GET request
                        response = await client.get(url)
                        
                        if response.status_code != 404:
                            status_emoji = "✅" if response.status_code == 200 else "⚠️"
                            print(f"{status_emoji} [{response.status_code}] GET {url}")
                            found_routes.append({
                                "method": "GET",
                                "url": url,
                                "status": response.status_code,
                                "endpoint": endpoint_name
                            })
                            
                            # If successful, show sample response
                            if response.status_code == 200:
                                try:
                                    data = response.json()
                                    print(f"      Sample response: {str(data)[:100]}...")
                                except:
                                    pass
                    except Exception as e:
                        pass
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
        
        print("\n" + "=" * 60)
        print("📊 Summary of Working Routes:")
        print("-" * 60)
        
        if found_routes:
            for route in found_routes:
                print(f"   {route['method']} {route['url']} [{route['status']}]")
        else:
            print("   ❌ No working routes found")
            print("\n💡 Suggestions:")
            print("   1. Check if the backend URL is correct")
            print("   2. Ask your backend team for:")
            print("      - API documentation URL")
            print("      - Correct base URL and endpoints")
            print("      - Sample working requests")
            print("   3. Check if API requires authentication")
        
        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(explore_api())