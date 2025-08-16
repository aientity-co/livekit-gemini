# LiveKit Voice Agent API Usage Guide

This document explains how to use the LiveKit Voice Agent API to make outbound calls.

## API Endpoints

### Base URL
```
http://your-vm-ip:8000
```

### 1. Health Check
**GET** `/health`

Check if the API is running.

**Response:**
```json
{
  "status": "healthy",
  "message": "LiveKit Voice Agent API is running"
}
```

### 2. Make a Call
**POST** `/call`

Initiate an outbound call to a phone number.

**Request Body:**
```json
{
  "phone_number": "+1234567890",
  "customer_name": "John Doe",
  "appointment_date": "2024-01-15",
  "appointment_time": "2:00 PM",
  "custom_instructions": "This is a follow-up call for appointment confirmation"
}
```

**Response:**
```json
{
  "call_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "initiated",
  "message": "Call to +1234567890 has been initiated"
}
```

### 3. Get Call Status
**GET** `/call/{call_id}`

Get the status of a specific call.

**Response:**
```json
{
  "status": "connected",
  "phone_number": "+1234567890",
  "customer_name": "John Doe",
  "appointment_date": "2024-01-15",
  "appointment_time": "2:00 PM",
  "custom_instructions": "This is a follow-up call for appointment confirmation",
  "room_name": "call-550e8400-e29b-41d4-a716-446655440000",
  "message": "Call connected successfully"
}
```

### 4. List All Calls
**GET** `/calls`

Get a list of all calls and their statuses.

**Response:**
```json
{
  "calls": {
    "550e8400-e29b-41d4-a716-446655440000": {
      "status": "connected",
      "phone_number": "+1234567890",
      "customer_name": "John Doe",
      "appointment_date": "2024-01-15",
      "appointment_time": "2:00 PM",
      "custom_instructions": "This is a follow-up call for appointment confirmation",
      "room_name": "call-550e8400-e29b-41d4-a716-446655440000",
      "message": "Call connected successfully"
    }
  }
}
```

## API Documentation

Once the API is running, you can access the interactive API documentation at:
```
http://your-vm-ip:8000/docs
```

This will show you the Swagger UI with all available endpoints and allow you to test them directly.

## Example Usage

### Using curl

```bash
# Make a call
curl -X POST "http://your-vm-ip:8000/call" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "customer_name": "John Doe",
    "appointment_date": "2024-01-15",
    "appointment_time": "2:00 PM"
  }'

# Check call status
curl "http://your-vm-ip:8000/call/550e8400-e29b-41d4-a716-446655440000"

# List all calls
curl "http://your-vm-ip:8000/calls"
```

### Using Python

```python
import requests

# Make a call
response = requests.post("http://your-vm-ip:8000/call", json={
    "phone_number": "+1234567890",
    "customer_name": "John Doe",
    "appointment_date": "2024-01-15",
    "appointment_time": "2:00 PM"
})

call_data = response.json()
call_id = call_data["call_id"]

# Check status
status_response = requests.get(f"http://your-vm-ip:8000/call/{call_id}")
status = status_response.json()
print(f"Call status: {status['status']}")
```

### Using JavaScript/Node.js

```javascript
// Make a call
const response = await fetch('http://your-vm-ip:8000/call', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    phone_number: '+1234567890',
    customer_name: 'John Doe',
    appointment_date: '2024-01-15',
    appointment_time: '2:00 PM'
  })
});

const callData = await response.json();
const callId = callData.call_id;

// Check status
const statusResponse = await fetch(`http://your-vm-ip:8000/call/${callId}`);
const status = await statusResponse.json();
console.log(`Call status: ${status.status}`);
```

## Call Status Values

- `initiated`: Call request has been received and is being processed
- `connecting`: Call is being connected to the phone number
- `dialing`: Phone number is being dialed
- `connected`: Call has been successfully connected
- `failed`: Call failed to connect

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `400`: Bad request (invalid phone number, missing required fields)
- `404`: Call not found
- `500`: Internal server error

Error responses include a detail message explaining what went wrong.

## Rate Limiting

Currently, there are no rate limits implemented. In production, you should consider implementing rate limiting to prevent abuse.

## Security Considerations

1. **Authentication**: The current implementation doesn't include authentication. For production use, implement proper authentication (API keys, JWT tokens, etc.).

2. **HTTPS**: Use HTTPS in production to encrypt API communications.

3. **Input Validation**: Phone numbers are validated for basic format, but you may want to add more sophisticated validation.

4. **CORS**: The API allows all origins (`*`). Configure this properly for production.
