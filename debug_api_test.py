# debug_api_test.py
# This will show us EXACTLY what the backend returns

import asyncio
import httpx


async def debug_api():
    base_url = "https://testbackend.educify.org/v1"
    
    print("🔍 Debugging API Responses...")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Student endpoint
        print("\n1️⃣  Testing GET /students/12345")
        print("-" * 60)
        try:
            response = await client.get(f"{base_url}/students/12345")
            print(f"Status Code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print(f"Raw Text Response: '{response.text}'")
            print(f"Response Length: {len(response.text)} bytes")
            
            if response.text.strip():
                try:
                    data = response.json()
                    print(f"✅ Valid JSON")
                    print(f"JSON Data: {data}")
                except:
                    print(f"❌ Not valid JSON")
            else:
                print(f"⚠️  Empty response body")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 2: Teachers endpoint
        print("\n2️⃣  Testing GET /teachers")
        print("-" * 60)
        try:
            response = await client.get(f"{base_url}/teachers")
            print(f"Status Code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print(f"Raw Text Response: '{response.text[:200]}'...")  # First 200 chars
            print(f"Response Length: {len(response.text)} bytes")
            
            if response.text.strip():
                try:
                    data = response.json()
                    print(f"✅ Valid JSON")
                    if isinstance(data, list):
                        print(f"JSON Data: List with {len(data)} items")
                        if data:
                            print(f"First item: {data[0]}")
                    else:
                        print(f"JSON Data: {data}")
                except:
                    print(f"❌ Not valid JSON")
            else:
                print(f"⚠️  Empty response body")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 3: Match endpoint with POST
        print("\n3️⃣  Testing POST /match")
        print("-" * 60)
        try:
            response = await client.post(
                f"{base_url}/match",
                json={
                    "studentId": "12345",
                    "matches": [
                        {"teacherId": "T001", "score": 0.95}
                    ]
                }
            )
            print(f"Status Code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print(f"Raw Text Response: '{response.text}'")
            print(f"Response Length: {len(response.text)} bytes")
            
            if response.text.strip():
                try:
                    data = response.json()
                    print(f"✅ Valid JSON")
                    print(f"JSON Data: {data}")
                except:
                    print(f"❌ Not valid JSON")
            else:
                print(f"⚠️  Empty response body")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 4: Try with actual filters
        print("\n4️⃣  Testing GET /teachers with filters")
        print("-" * 60)
        try:
            response = await client.get(
                f"{base_url}/teachers",
                params={"subject": "Mathematics", "location": "Lagos"}
            )
            print(f"Status Code: {response.status_code}")
            print(f"Raw Text Response: '{response.text[:200]}'...")
            
            if response.text.strip():
                try:
                    data = response.json()
                    print(f"✅ Valid JSON")
                    print(f"Data type: {type(data)}")
                    print(f"Data: {data}")
                except:
                    print(f"❌ Not valid JSON")
            else:
                print(f"⚠️  Empty response")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("\n💡 What we learned:")
    print("   - Check if responses are empty or have data")
    print("   - Check Content-Type header")
    print("   - Might need authentication or different params")


if __name__ == "__main__":
    asyncio.run(debug_api())