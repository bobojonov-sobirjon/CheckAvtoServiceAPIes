# Swagger JWT Authentication Guide

## 🔐 How to Use JWT Authentication in Swagger

### Step 1: Get JWT Token
First, you need to get a JWT token by authenticating:

**POST** `/api/auth/login/`
```json
{
    "phone_number": "7914180518"
}
```

**POST** `/api/auth/check-sms-code/`
```json
{
    "phone_number": "7914180518",
    "sms_code": "1234"
}
```

**Response:**
```json
{
    "success": true,
    "tokens": {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
}
```

### Step 2: Use JWT Token in Swagger

1. **Open Swagger UI** at `http://127.0.0.1:8000/swagger/`

2. **Click "Authorize" button** (🔒 icon) in the top right

3. **Enter JWT Token:**
   - In the "Value" field, enter: `Bearer YOUR_JWT_TOKEN`
   - Example: `Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...`

4. **Click "Authorize"**

5. **Click "Close"**

### Step 3: Test APIs
Now you can test all the APIs:
- ✅ Car APIs (if you're in Driver group)
- ✅ Master APIs (if you're in Master group)

## 🚗 Car API Endpoints

### Get User's Cars
**GET** `/api/car/cars/`
- No body required
- Returns list of user's cars

### Create New Car
**POST** `/api/car/cars/`
```json
{
    "type_car": "Легковой",
    "brand": "Toyota",
    "model": "Camry",
    "year": 2020
}
```

### Get Car Details
**GET** `/api/car/cars/{id}/`
- Replace `{id}` with actual car ID

### Update Car
**PUT** `/api/car/cars/{id}/`
```json
{
    "type_car": "Легковой",
    "brand": "BMW",
    "model": "X5",
    "year": 2022
}
```

### Delete Car
**DELETE** `/api/car/cars/{id}/`
- No body required

### Get Car Statistics
**GET** `/api/car/cars/stats/`
- No body required

## 🔧 Master API Endpoints

### Get Master Profile
**GET** `/api/master/masters/`
- No body required

### Create Master Profile
**POST** `/api/master/masters/`
```json
{
    "city": "Москва",
    "services": ["diagnostics", "service"],
    "card_number": "1234 1234 1234 1234",
    "card_expiry_month": 12,
    "card_expiry_year": 2025,
    "card_cvv": "123"
}
```

### Update Master Profile
**PUT** `/api/master/masters/`
```json
{
    "city": "Санкт-Петербург",
    "services": ["diagnostics", "tire_repair"],
    "card_number": "5678 5678 5678 5678",
    "card_expiry_month": 6,
    "card_expiry_year": 2026,
    "card_cvv": "456"
}
```

### Get Service Types
**GET** `/api/master/masters/service-types/`
- No body required

### Add Service
**POST** `/api/master/masters/add-service/`
```json
{
    "service_code": "car_wash"
}
```

### Remove Service
**POST** `/api/master/masters/remove-service/`
```json
{
    "service_code": "car_wash"
}
```

### Get Master Statistics
**GET** `/api/master/masters/stats/`
- No body required

## 🔑 Important Notes

1. **JWT Token Format:** Always use `Bearer ` prefix
2. **Token Expiry:** JWT tokens expire, get a new one if needed
3. **Group Permissions:** 
   - Driver group can only access Car APIs
   - Master group can only access Master APIs
4. **User Data:** Users can only see their own data

## 🚨 Troubleshooting

### "Authorization header not found"
- Make sure you clicked "Authorize" and entered the token correctly
- Check that the token format is `Bearer YOUR_TOKEN`

### "Invalid token"
- Your JWT token might be expired
- Get a new token by logging in again

### "Permission denied"
- Check if your user is in the correct group (Driver or Master)
- Add user to group via Django admin

### "User not found"
- Make sure you're logged in and have a valid JWT token
