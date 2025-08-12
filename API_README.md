# Digital Time Capsule API

This is a FastAPI backend for the Digital Time Capsule application, designed to work with a React frontend.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (optional):
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_BUCKET=capsules
UPLOAD_DIR=./uploads
CHECK_INTERVAL_SECONDS=60
```

3. Run the server:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health Check
- `GET /` - API status
- `GET /api/health` - Health check endpoint

### Capsules

#### Get all capsules for an owner
- `GET /api/capsules?owner=alice@example.com`
- Returns: Array of capsule objects

#### Create a new capsule
- `POST /api/capsules`
- Body: Form data with capsule info and optional files
- Returns: Created capsule object

#### Get a specific capsule
- `GET /api/capsules/{capsule_id}`
- Returns: Capsule object with files and unlock status

#### Manually unlock a capsule
- `POST /api/capsules/{capsule_id}/unlock`
- Returns: Success message

## Data Models

### CapsuleCreate
```json
{
  "title": "string",
  "owner": "string", 
  "unlockDate": "YYYY-MM-DD",
  "message": "string (optional)"
}
```

### CapsuleResponse
```json
{
  "id": 1,
  "title": "string",
  "owner": "string",
  "message": "string",
  "unlock_date": 1234567890000,
  "created_at": 1234567890000,
  "is_unlocked": false
}
```

### FileResponse
```json
{
  "id": 1,
  "original_name": "string",
  "url": "string (optional)",
  "mimetype": "string"
}
```

## Features

- **CORS enabled** for React frontend integration
- **File upload support** with Supabase storage or local fallback
- **Automatic capsule unlocking** via background worker
- **Local storage fallback** when Supabase is unavailable
- **Pydantic validation** for request/response models

## React Integration

The API is configured to accept requests from:
- `http://localhost:3000` (Create React App)
- `http://localhost:5173` (Vite)

You can modify the CORS origins in `main.py` if needed.

## Example Usage

### Create a capsule with files
```javascript
const formData = new FormData();
formData.append('title', 'My Time Capsule');
formData.append('owner', 'alice@example.com');
formData.append('unlockDate', '2024-12-31');
formData.append('message', 'Happy New Year!');
formData.append('files', file1);
formData.append('files', file2);

const response = await fetch('http://localhost:8000/api/capsules', {
  method: 'POST',
  body: formData
});
```

### Get capsules for an owner
```javascript
const response = await fetch('http://localhost:8000/api/capsules?owner=alice@example.com');
const capsules = await response.json();
```
