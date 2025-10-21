# Order API Documentation

## Overview
Complete Order management system with CRUD operations, filtering, and role-based access control.

## API Endpoints

### 1. Order List and Create
**GET/POST** `/api/order/`

#### GET - List Orders
- **Authentication**: Required
- **Permissions**: Users see only their orders, Masters see only assigned orders
- **Filters**: 
  - `status` - Filter by order status
  - `priority` - Filter by order priority  
  - `master` - Filter by master ID
- **Search**: Search in text, location, user name, user email
- **Ordering**: `created_at`, `updated_at`, `status`, `priority` (default: `-created_at`)

#### POST - Create Order
- **Authentication**: Required
- **Body**:
```json
{
    "text": "Order description",
    "priority": "low|high",
    "data": {},
    "location": "Address or location description",
    "latitude": 55.7558,
    "longitude": 37.6176,
    "master": 1
}
```

### 2. Order Detail, Update, Delete
**GET/PUT/DELETE** `/api/order/{id}/`

#### GET - Retrieve Order
- **Authentication**: Required
- **Permissions**: Order owner or assigned master

#### PUT - Update Order
- **Authentication**: Required
- **Permissions**: Order owner or assigned master
- **Body**:
```json
{
    "text": "Updated description",
    "status": "pending|in_progress|completed|cancelled|rejected",
    "priority": "low|high",
    "data": {},
    "location": "Updated location",
    "latitude": 55.7558,
    "longitude": 37.6176,
    "master": 1
}
```

#### DELETE - Delete Order
- **Authentication**: Required
- **Permissions**: Order owner or assigned master

### 3. Filter by Name
**GET** `/api/order/by-name/?name={name}`

- **Authentication**: Required
- **Query Parameters**: `name` (required) - Search by user name
- **Description**: Search orders by user's first name, last name, or full name

### 4. Orders by User
**GET** `/api/order/by-user/{user_id}/`

- **Authentication**: Required
- **Permissions**: User can only see their own orders, Masters can see any user's orders
- **Description**: Get all orders for a specific user

### 5. Orders by Master
**GET** `/api/order/by-master/{master_id}/`

- **Authentication**: Required
- **Permissions**: Only Masters, can only see their own orders
- **Description**: Get all orders assigned to a specific master

### 6. Assign Order to Master
**POST** `/api/order/{order_id}/assign/`

- **Authentication**: Required
- **Permissions**: Masters only
- **Description**: Assign an order to the current master

### 7. Update Order Status
**POST** `/api/order/{order_id}/status/`

- **Authentication**: Required
- **Permissions**: Order owner or assigned master
- **Body**:
```json
{
    "status": "pending|in_progress|completed|cancelled|rejected"
}
```

## Order Model Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key (read-only) |
| `user` | ForeignKey | User who created the order |
| `text` | TextField | Order description |
| `status` | CharField | Order status (choices) |
| `priority` | CharField | Order priority (low/high) |
| `data` | JSONField | Additional data |
| `location` | TextField | Location description |
| `latitude` | DecimalField | Latitude coordinate |
| `longitude` | DecimalField | Longitude coordinate |
| `master` | ForeignKey | Assigned master |
| `created_at` | DateTimeField | Creation timestamp (read-only) |
| `updated_at` | DateTimeField | Last update timestamp (read-only) |

## Order Status Options
- `pending` - Ожидает
- `in_progress` - В работе  
- `completed` - Завершен
- `cancelled` - Отменен
- `rejected` - Отклонен

## Order Priority Options
- `low` - Низкий
- `high` - Высокий

## Permissions

### IsOrderOwner
- Allows access only to the order owner

### IsMaster  
- Allows access only to users with master profile

### IsOrderOwnerOrMaster
- Allows access to order owner or assigned master

### IsOrderOwnerOrReadOnly
- Allows read access to all authenticated users
- Allows write access only to order owner

## Admin Interface

The admin interface includes:
- **List Display**: ID, User, Status (with color badges), Priority (with color badges), Master, Location, Timestamps
- **Filters**: Status, Priority, Creation date, Update date, Master city, Master
- **Search**: ID, Text, Location, User names, Master names
- **Fieldsets**: Organized sections for better UX
- **Read-only Fields**: ID, timestamps, user/master links
- **Permissions**: Superuser-only add/delete, all users can view/edit

## Usage Examples

### Create an Order
```bash
curl -X POST "http://localhost:8000/api/order/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Need car diagnostics",
    "priority": "high",
    "location": "123 Main St, City",
    "latitude": 55.7558,
    "longitude": 37.6176
  }'
```

### Get Orders with Filters
```bash
curl -X GET "http://localhost:8000/api/order/?status=pending&priority=high" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Search Orders by Name
```bash
curl -X GET "http://localhost:8000/api/order/by-name/?name=John" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update Order Status
```bash
curl -X POST "http://localhost:8000/api/order/1/status/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'
```

## Error Responses

### 400 Bad Request
```json
{
    "error": "Validation error message"
}
```

### 403 Forbidden
```json
{
    "error": "У вас нет прав для выполнения этого действия"
}
```

### 404 Not Found
```json
{
    "error": "Заказ не найден"
}
```

## Notes
- All endpoints require JWT authentication
- Users can only see their own orders unless they are masters
- Masters can only see orders assigned to them
- Order assignment automatically changes status to "in_progress"
- Latitude/longitude validation: -90 to 90 for latitude, -180 to 180 for longitude

