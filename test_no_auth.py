# test_no_auth.py
# Test if the API works WITHOUT authentication

import asyncio
import httpx


async def test_without_auth():
    base_url = "https://testbackend.educify.org/api/docs/mirzaKey/#/"
    
    print("Testing API WITHOUT Authentication...")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Get all teachers (no auth)
        print("\n1. Testing GET /api/v1/teachers (no auth)")
        print("-" * 60)
        try:
            response = await client.get(f"{base_url}/teachers")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ SUCCESS! No auth needed")
                try:
                    data = response.json()
                    print(f"Response type: {type(data)}")
                    if isinstance(data, list):
                        print(f"Number of teachers: {len(data)}")
                        if data:
                            print(f"\nFirst teacher sample:")
                            print(f"  Keys: {list(data[0].keys())}")
                            print(f"  Full data: {data[0]}")
                    else:
                        print(f"Response: {data}")
                except Exception as e:
                    print(f"Error parsing JSON: {e}")
                    print(f"Raw response: {response.text[:500]}")
            elif response.status_code == 401:
                print("❌ Authentication required (401)")
            elif response.status_code == 403:
                print("❌ Forbidden (403)")
            else:
                print(f"⚠️ Status {response.status_code}")
                print(f"Response: {response.text[:200]}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 2: Get specific student (no auth)
        print("\n2. Testing GET /api/v1/students/12345 (no auth)")
        print("-" * 60)
        try:
            response = await client.get(f"{base_url}/students/12345")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ SUCCESS! No auth needed")
                try:
                    data = response.json()
                    print(f"Student ID: {data.get('id')}")
                    print(f"Keys: {list(data.keys())}")
                    print(f"Full data: {data}")
                except Exception as e:
                    print(f"Error parsing JSON: {e}")
            elif response.status_code == 401:
                print("❌ Authentication required (401)")
            elif response.status_code == 404:
                print("⚠️ Student not found (404) - try different ID")
            else:
                print(f"Status: {response.status_code}")
                print(f"Response: {response.text[:200]}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 3: Create booking (no auth)
        print("\n3. Testing POST /api/v1/bookings (no auth)")
        print("-" * 60)
        try:
            test_booking = {
                "booking": {
                    "studentId": "12345",
                    "teacherId": "T001",
                    "type": "WEEKLY",
                    "location": "online"
                }
            }
            response = await client.post(
                f"{base_url}/bookings",
                json=test_booking
            )
            print(f"Status Code: {response.status_code}")
            
            if response.status_code in [200, 201]:
                print("✅ SUCCESS! No auth needed")
                print(f"Response: {response.json()}")
            elif response.status_code == 401:
                print("❌ Authentication required (401)")
            else:
                print(f"Status: {response.status_code}")
                print(f"Response: {response.text[:300]}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("\n📋 Summary:")
    print("If you see ✅ SUCCESS - we can proceed without auth!")
    print("If you see ❌ 401 - we need authentication")
    print("\nIf it works, I'll update the full code now.")


if __name__ == "__main__":
    asyncio.run(test_without_auth())