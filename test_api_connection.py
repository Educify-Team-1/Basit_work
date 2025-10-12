"""
Test script to verify API connection works with correct paths

Run this to test the backend API connection:
python test_api_connection.py
"""

import asyncio
import httpx


async def test_api_connection():
    # FIXED: Correct base URL with /v1
    base_url = "https://testbackend.educify.org/api/docs/mirzaKey/#/"
    
    print("Testing Backend API Connection (FIXED PATHS)...")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Get a student
        print("\n1. Testing GET /students/{id}")
        try:
            response = await client.get(f"{base_url}/students/12345")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ SUCCESS!")
                data = response.json()
                print(f"   Response keys: {list(data.keys())}")
                print(f"   Full Response: {data}")
            else:
                print(f"   ❌ FAILED")
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
        
        # Test 2: Get teachers
        print("\n2. Testing GET /teachers")
        try:
            response = await client.get(
                f"{base_url}/teachers",
                params={"subject": "Mathematics", "location": "Lagos"}
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ SUCCESS!")
                data = response.json()
                # Handle if response is wrapped in 'data' key
                if isinstance(data, dict) and "data" in data:
                    teachers = data["data"]
                else:
                    teachers = data
                
                if isinstance(teachers, list):
                    print(f"   Found {len(teachers)} teachers")
                    if teachers:
                        print(f"   Response keys: {list(teachers[0].keys())}")
                        print(f"   First teacher: {teachers[0]}")
                else:
                    print(f"   Response: {data}")
            else:
                print(f"   ❌ FAILED")
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
        
        # Test 3: Send match results
        print("\n3. Testing POST /match")
        try:
            response = await client.post(
                f"{base_url}/match",
                json={
                    "studentId": "12345",
                    "matches": [
                        {"teacherId": "T001", "score": 0.95},
                        {"teacherId": "T002", "score": 0.87}
                    ]
                }
            )
            print(f"   Status: {response.status_code}")
            if response.status_code in [200, 201]:
                print(f"   ✅ SUCCESS!")
                print(f"   Response: {response.json()}")
            else:
                print(f"   ❌ FAILED")
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    print("\n" + "=" * 50)
    print("API Connection Test Complete!")
    print("\n💡 Next Steps:")
    print("   1. Check the response keys above")
    print("   2. Update .env to set DATA_SOURCE=api")
    print("   3. Run: uvicorn app.main:app --reload")


if __name__ == "__main__":
    asyncio.run(test_api_connection())