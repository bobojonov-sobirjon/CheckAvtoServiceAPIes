#!/usr/bin/env python3
"""
Test JWT authentication
"""
import requests
import json

def test_jwt_auth():
    base_url = "http://127.0.0.1:8000"
    
    print("🔐 Testing JWT Authentication...")
    
    # Step 1: Login (send SMS)
    print("\n1. Sending SMS...")
    login_data = {
        "phone_number": "7914180518"
    }
    
    try:
        response = requests.post(f"{base_url}/api/auth/login/", json=login_data)
        print(f"Login response: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SMS sent successfully!")
            print("Please check your phone for the SMS code and enter it below:")
            
            sms_code = input("Enter the 4-digit SMS code: ")
            
            # Step 2: Verify SMS code
            print("\n2. Verifying SMS code...")
            verify_data = {
                "phone_number": "7914180518",
                "sms_code": sms_code
            }
            
            response = requests.post(f"{base_url}/api/auth/check-sms-code/", json=verify_data)
            print(f"Verify response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ JWT token received!")
                print(f"Access token: {data['tokens']['access'][:50]}...")
                
                # Step 3: Test protected endpoint
                print("\n3. Testing protected endpoint...")
                headers = {
                    "Authorization": f"Bearer {data['tokens']['access']}"
                }
                
                # Test car API
                response = requests.get(f"{base_url}/api/car/cars/", headers=headers)
                print(f"Car API response: {response.status_code}")
                print(f"Response: {response.json()}")
                
                if response.status_code == 200:
                    print("✅ Car API accessible!")
                elif response.status_code == 403:
                    print("❌ User not in Driver group - add user to Driver group via Django admin")
                else:
                    print(f"❌ Car API error: {response.json()}")
                    
            else:
                print(f"❌ SMS verification failed: {response.json()}")
        else:
            print(f"❌ SMS sending failed: {response.json()}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running. Please start the server first.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_jwt_auth()
