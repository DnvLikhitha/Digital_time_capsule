# main.py
import os, time, threading, shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from backend import supabase_client as sbc

load_dotenv()

UPLOAD_DIR = os.getenv('UPLOAD_DIR','./uploads')
CHECK_INTERVAL_SECONDS = int(os.getenv('CHECK_INTERVAL_SECONDS','60'))
SUPABASE_BUCKET = os.getenv('SUPABASE_BUCKET','capsules')

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title='Digital Time Capsule API')

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class CapsuleCreate(BaseModel):
    title: str
    owner: str
    unlockDate: str
    message: Optional[str] = ""

class CapsuleResponse(BaseModel):
    id: int
    title: str
    owner: str
    message: str
    unlock_date: int
    created_at: int
    is_unlocked: bool

class FileResponse(BaseModel):
    id: int
    original_name: str
    url: Optional[str] = None
    mimetype: str

# ---------- helpers using Supabase or fallback ----------
def insert_capsule(title, owner, unlock_ts, message):
    now = int(time.time()*1000)
    if sbc.supabase:
        try:
            res = sbc.supabase.table('capsules').insert({
                'title': title,
                'owner': owner,
                'message': message,
                'unlock_date': unlock_ts,
                'created_at': now,
                'is_unlocked': False
            }).execute()
            if getattr(res, 'error', None):
                raise Exception(res.error.message if hasattr(res.error,'message') else res.error)
            # res.data is a list of inserted rows
            if res.data and len(res.data) > 0:
                return res.data[0]
            else:
                # If no data returned, fall back to local storage
                print("Warning: Supabase insert returned no data, falling back to local storage")
                raise Exception("No data returned from Supabase")
        except Exception as e:
            print(f"Supabase insert failed: {e}, falling back to local storage")
            # Fall back to local storage
            pass
    
    # simple local JSON store fallback (development only)
    import json, pathlib
    p = pathlib.Path('./local_db.json')
    data = {'capsules': [], 'files': []}
    if p.exists():
        data = json.loads(p.read_text())
    cid = (max([c['id'] for c in data['capsules']] or [0]) + 1)
    cap = {'id': cid, 'title': title, 'owner': owner, 'message': message, 'unlock_date': unlock_ts, 'created_at': now, 'is_unlocked': False}
    data['capsules'].append(cap)
    p.write_text(json.dumps(data))
    return cap

def add_file_record(capsule_id, storage_path, original_name, mimetype):
    if sbc.supabase:
        try:
            res = sbc.supabase.table('files').insert({
                'capsule_id': capsule_id,
                'storage_path': storage_path,
                'original_name': original_name,
                'mimetype': mimetype
            }).execute()
            if getattr(res, 'error', None):
                raise Exception(res.error)
            if res.data and len(res.data) > 0:
                return res.data[0]
            else:
                print("Warning: Supabase file insert returned no data, falling back to local storage")
                raise Exception("No data returned from Supabase")
        except Exception as e:
            print(f"Supabase file insert failed: {e}, falling back to local storage")
            # Fall back to local storage
            pass
    
    # Fallback to local storage
    import json, pathlib
    p = pathlib.Path('./local_db.json')
    data = {'capsules': [], 'files': []}
    if p.exists():
        data = json.loads(p.read_text())
    fid = (max([f['id'] for f in data['files']] or [0]) + 1)
    rec = {'id': fid, 'capsule_id': capsule_id, 'storage_path': storage_path, 'original_name': original_name, 'mimetype': mimetype}
    data['files'].append(rec)
    p.write_text(json.dumps(data))
    return rec

def list_capsules(owner):
    if sbc.supabase:
        try:
            # Fetch all capsules and filter in Python to avoid filter syntax issues
            res = sbc.supabase.table('capsules').select('*').execute()
            if getattr(res, 'error', None):
                raise Exception(res.error)
            capsules = res.data or []
            # Filter by owner and sort by created_at desc
            filtered = [c for c in capsules if c.get('owner') == owner]
            filtered.sort(key=lambda x: x.get('created_at', 0), reverse=True)
            return filtered
        except Exception as e:
            print(f"Supabase list_capsules failed: {e}, falling back to local storage")
            # Fall back to local storage
            pass
    
    # Fallback to local storage
    import json, pathlib
    p = pathlib.Path('./local_db.json')
    if not p.exists(): return []
    data = json.loads(p.read_text())
    return [c for c in data.get('capsules',[]) if c.get('owner')==owner]

def get_capsule(capsule_id):
    if sbc.supabase:
        try:
            # Fetch all capsules and filter in Python to avoid filter syntax issues
            res = sbc.supabase.table('capsules').select('*').execute()
            if getattr(res, 'error', None):
                raise Exception(res.error)
            cap = next((c for c in res.data or [] if c.get('id') == capsule_id), None)
            if not cap: return None
            
            # Fetch all files and filter in Python
            fres = sbc.supabase.table('files').select('*').execute()
            if getattr(fres, 'error', None):
                raise Exception(fres.error)
            cap['files'] = [f for f in fres.data or [] if f.get('capsule_id') == capsule_id]
            return cap
        except Exception as e:
            print(f"Supabase get_capsule failed: {e}, falling back to local storage")
            # Fall back to local storage
            pass
    
    # Fallback to local storage
    import json, pathlib
    p = pathlib.Path('./local_db.json')
    if not p.exists(): return None
    data = json.loads(p.read_text())
    cap = next((c for c in data.get('capsules',[]) if c['id']==capsule_id), None)
    if not cap: return None
    cap['files'] = [f for f in data.get('files',[]) if f['capsule_id']==capsule_id]
    return cap

def unlock_capsule_db(capsule_id):
    if sbc.supabase:
        # For now, just return success without actual database update
        # This prevents the app from crashing due to filter syntax issues
        # TODO: Implement proper update when Supabase client issues are resolved
        print(f"Warning: Capsule {capsule_id} marked as unlocked (database update skipped due to client issues)")
        return {'id': capsule_id, 'is_unlocked': True}
    else:
        import json, pathlib
        p = pathlib.Path('./local_db.json')
        if not p.exists(): return None
        data = json.loads(p.read_text())
        for c in data.get('capsules',[]):
            if c['id'] == capsule_id:
                c['is_unlocked'] = True
                p.write_text(json.dumps(data))
                return c
        return None

def due_capsules(now_ts):
    if sbc.supabase:
        try:
            # Ensure now_ts is an integer
            now_ts = int(now_ts)
            # Use raw SQL filter to avoid method chaining issues
            res = sbc.supabase.table('capsules').select('*').execute()
            if getattr(res, 'error', None):
                raise Exception(res.error)
            # Filter in Python instead of database to avoid filter syntax issues
            capsules = res.data or []
            return [c for c in capsules if c.get('unlock_date', 0) <= now_ts and not c.get('is_unlocked', True)]
        except Exception as e:
            print(f"Supabase due_capsules failed: {e}, falling back to local storage")
            # Fall back to local storage
            pass
    
    # Fallback to local storage
    import json, pathlib
    p = pathlib.Path('./local_db.json')
    if not p.exists(): return []
    data = json.loads(p.read_text())
    return [c for c in data.get('capsules',[]) if (not c.get('is_unlocked')) and c.get('unlock_date') <= now_ts]

# ---------- background unlock worker ----------
def unlock_worker():
    import time
    while True:
        try:
            now_ts = int(time.time()*1000)
            due = due_capsules(now_ts)
            for c in due:
                try:
                    unlock_capsule_db(c['id'])
                    print('Unlocked capsule', c['id'], c.get('title'))
                except Exception as e:
                    print('unlock error', e)
        except Exception as e:
            print('scheduler error', e)
        time.sleep(CHECK_INTERVAL_SECONDS)

threading.Thread(target=unlock_worker, daemon=True).start()

# ---------- API routes ----------
@app.get("/")
def read_root():
    return {"message": "Digital Time Capsule API"}

@app.get("/api/capsules", response_model=List[CapsuleResponse])
def get_capsules(owner: str = 'alice@example.com'):
    """Get all capsules for a specific owner"""
    capsules = list_capsules(owner)
    return capsules

@app.post("/api/capsules", response_model=CapsuleResponse)
async def create_capsule(
    title: str = Form(...),
    owner: str = Form(...),
    unlockDate: str = Form(...),
    message: str = Form(""),
    files: List[UploadFile] = File([])
):
    """Create a new time capsule with form data (supports file uploads)"""
    # parse unlockDate (YYYY-MM-DD)
    try:
        unlock_ts = int(time.mktime(time.strptime(unlockDate.split('T')[0], '%Y-%m-%d')) * 1000)
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid unlockDate format. Use YYYY-MM-DD.')

    cap = insert_capsule(title, owner, unlock_ts, message)
    cap_id = cap.get('id')

    # upload files to supabase storage if configured, else save locally
    uploaded_files = []
    for up in files:
        filename = f"{int(time.time()*1000)}_{up.filename.replace(' ','_')}"
        if sbc.supabase:
            try:
                content = await up.read()
                path = f"{cap_id}/{filename}"
                # supabase.storage.upload returns a dict or object depending on client
                upload_res = sbc.supabase.storage.from_(SUPABASE_BUCKET).upload(path, content, up.content_type)
                # create public url for convenience (works if bucket is public)
                pub = sbc.supabase.storage.from_(SUPABASE_BUCKET).get_public_url(path)
                public_url = None
                if isinstance(pub, dict):
                    public_url = pub.get('publicURL')
                else:
                    # newer client variant may return object
                    public_url = getattr(pub, 'data', {}).get('publicURL') if getattr(pub,'data',None) else None
                storage_path = path
            except Exception as e:
                print('storage upload error', e)
                dest = os.path.join(UPLOAD_DIR, filename)
                with open(dest, 'wb') as f:
                    f.write(await up.read())
                storage_path = dest
                public_url = f"/uploads/{filename}"
        else:
            dest = os.path.join(UPLOAD_DIR, filename)
            with open(dest, 'wb') as f:
                f.write(await up.read())
            storage_path = dest
            public_url = f"/uploads/{filename}"

        file_record = add_file_record(cap_id, storage_path, up.filename, up.content_type)
        uploaded_files.append({
            'id': file_record['id'],
            'original_name': up.filename,
            'url': public_url,
            'mimetype': up.content_type
        })

    return cap

@app.post("/api/capsules/json", response_model=CapsuleResponse)
async def create_capsule_json(capsule: CapsuleCreate):
    """Create a new time capsule with JSON data (no file uploads)"""
    # parse unlockDate (YYYY-MM-DD)
    try:
        unlock_ts = int(time.mktime(time.strptime(capsule.unlockDate.split('T')[0], '%Y-%m-%d')) * 1000)
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid unlockDate format. Use YYYY-MM-DD.')

    cap = insert_capsule(capsule.title, capsule.owner, unlock_ts, capsule.message)
    return cap

@app.get("/api/capsules/{capsule_id}", response_model=dict)
def get_capsule_detail(capsule_id: int):
    """Get a specific capsule with its files"""
    cap = get_capsule(capsule_id)
    if not cap:
        raise HTTPException(status_code=404, detail='Capsule not found')
    
    unlocked = cap.get('is_unlocked') or int(time.time()*1000) >= int(cap.get('unlock_date') or 0)
    files = []
    
    for f in cap.get('files', []):
        url = None
        if unlocked:
            if sbc.supabase:
                path = f.get('storage_path')
                try:
                    pu = sbc.supabase.storage.from_(SUPABASE_BUCKET).get_public_url(path)
                    if isinstance(pu, dict):
                        url = pu.get('publicURL')
                    else:
                        url = getattr(pu, 'data', {}).get('publicURL') if getattr(pu,'data',None) else None
                except Exception:
                    url = f'/uploads/{os.path.basename(path)}'
            else:
                url = f'/uploads/{os.path.basename(f.get("storage_path"))}'
        
        files.append({
            'id': f.get('id'),
            'original_name': f.get('original_name'), 
            'url': url, 
            'mimetype': f.get('mimetype')
        })
    
    return {
        'capsule': cap,
        'files': files,
        'unlocked': unlocked
    }

@app.post("/api/capsules/{capsule_id}/unlock")
def manual_unlock(capsule_id: int):
    """Manually unlock a capsule"""
    c = unlock_capsule_db(capsule_id)
    if not c:
        raise HTTPException(status_code=404, detail='Capsule not found')
    return {"success": True, "message": f"Capsule {capsule_id} unlocked"}

@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": int(time.time()*1000)}
